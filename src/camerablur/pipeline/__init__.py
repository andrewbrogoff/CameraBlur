"""Main pipeline orchestrator for CameraBlur."""

import signal
import threading
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Callable, Optional, Union

import cv2

from ..background.loader import ImageBackground, load_background
from ..background.video_loop import VideoLoop
from ..config import AppConfig, EffectMode, SegmentationBackend
from ..utils.performance import FPSCounter
from .capture import CameraCapture
from .effects import EffectsProcessor
from .output import VirtualCameraOutput
from .rvm_segmenter import RVMSegmenter
from .segmentation import Segmenter


class PipelineCommand(Enum):
    """Commands that can be sent to the pipeline."""

    SET_BLUR_INTENSITY = auto()
    SET_FEATHER_AMOUNT = auto()
    SET_EFFECT_MODE = auto()
    SET_BACKGROUND = auto()
    STOP = auto()


@dataclass
class Command:
    """A command to be processed by the pipeline."""

    type: PipelineCommand
    value: Any = None


class VirtualCameraPipeline:
    """Main pipeline orchestrating all components."""

    def __init__(self, config: AppConfig):
        """Initialize the pipeline.

        Args:
            config: Application configuration.
        """
        self._config = config
        self._capture: Optional[CameraCapture] = None
        self._segmenter: Optional[Union[Segmenter, RVMSegmenter]] = None
        self._effects: Optional[EffectsProcessor] = None
        self._output: Optional[VirtualCameraOutput] = None
        self._background: Optional[Union[ImageBackground, VideoLoop]] = None
        self._fps_counter = FPSCounter()
        self._running = False
        self._print_fps = True
        self._command_queue: Queue[Command] = Queue()
        self._fps_callback: Optional[Callable[[float], None]] = None

    def set_fps_callback(self, callback: Optional[Callable[[float], None]]) -> None:
        """Set callback for FPS updates.

        Args:
            callback: Function to call with FPS value, or None to disable.
        """
        self._fps_callback = callback

    def queue_command(self, command: Command) -> None:
        """Queue a command for thread-safe execution in the pipeline loop.

        Args:
            command: Command to execute.
        """
        self._command_queue.put(command)

    def request_stop(self) -> None:
        """Request the pipeline to stop (thread-safe)."""
        self._command_queue.put(Command(PipelineCommand.STOP))

    def _process_commands(self) -> bool:
        """Process queued commands.

        Returns:
            False if stop was requested, True otherwise.
        """
        try:
            while True:
                cmd = self._command_queue.get_nowait()
                if cmd.type == PipelineCommand.STOP:
                    return False
                elif cmd.type == PipelineCommand.SET_BLUR_INTENSITY:
                    if self._effects:
                        self._effects.update_blur_intensity(cmd.value)
                elif cmd.type == PipelineCommand.SET_FEATHER_AMOUNT:
                    if self._effects:
                        self._effects.update_feather_amount(cmd.value)
                elif cmd.type == PipelineCommand.SET_EFFECT_MODE:
                    if self._effects:
                        self._effects.update_mode(cmd.value)
                elif cmd.type == PipelineCommand.SET_BACKGROUND:
                    self._handle_background_change(cmd.value)
        except Empty:
            pass
        return True

    def _handle_background_change(self, path: Optional[Path]) -> None:
        """Handle background change at runtime.

        Args:
            path: Path to new background, or None to clear.
        """
        if isinstance(self._background, VideoLoop):
            self._background.stop()
            self._background = None

        if path is None:
            self._background = None
            if self._effects:
                self._effects.set_background_source(None)
        else:
            self._load_background(path)

    @property
    def current_blur_intensity(self) -> int:
        """Get current blur intensity."""
        return self._config.effect.blur_intensity

    @property
    def current_feather_amount(self) -> int:
        """Get current feather amount."""
        return self._config.effect.feather_amount

    @property
    def current_effect_mode(self) -> EffectMode:
        """Get current effect mode."""
        return self._config.effect.mode

    @property
    def is_running(self) -> bool:
        """Check if pipeline is currently running."""
        return self._running

    def _setup_signal_handlers(self) -> None:
        """Setup handlers for graceful shutdown.

        Only works when called from the main thread.
        """
        # Signal handlers can only be set from the main thread
        if threading.current_thread() is not threading.main_thread():
            return

        def handler(signum, frame):
            self._running = False

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def start(self) -> None:
        """Start all pipeline components."""
        self._capture = CameraCapture(self._config.camera)
        self._capture.start()

        width, height = self._capture.get_frame_size()

        # Select segmenter based on backend configuration
        if self._config.segmentation.backend == SegmentationBackend.RVM:
            self._segmenter = RVMSegmenter(self._config.segmentation)
        else:
            self._segmenter = Segmenter(self._config.segmentation)
        self._segmenter.start()

        self._effects = EffectsProcessor(self._config.effect)

        if self._config.effect.background_path is not None:
            self._load_background(self._config.effect.background_path)

        self._output = VirtualCameraOutput(
            self._config.output,
            width,
            height,
            self._config.camera.fps,
        )
        device = self._output.start()
        print(f"Virtual camera started on {device}")

    def _load_background(self, path: Path) -> None:
        """Load and set background source.

        Args:
            path: Path to background file.
        """
        self._background = load_background(path)
        if self._effects is not None:
            self._effects.set_background_source(self._background)

    def run(self) -> None:
        """Run the main processing loop."""
        self._setup_signal_handlers()
        self._running = True

        if self._print_fps:
            print("Processing... Press Ctrl+C to stop")

        while self._running:
            if not self._process_commands():
                break

            frame = self._capture.read()
            if frame is None:
                continue

            mask = self._segmenter.process(frame)

            result = self._effects.process(frame, mask)

            self._output.write(result)

            if self._config.debug.preview_window:
                cv2.imshow("CameraBlur Preview", result)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self._running = False

            self._fps_counter.tick()
            fps = self._fps_counter.get_fps()
            if self._fps_callback is not None:
                self._fps_callback(fps)
            if self._print_fps:
                report = self._fps_counter.get_report()
                if report:
                    print(f"\r{report}", end="", flush=True)

        if self._print_fps:
            print("\nStopping...")

    def stop(self) -> None:
        """Stop all pipeline components."""
        if self._config.debug.preview_window:
            cv2.destroyAllWindows()

        if self._background is not None and isinstance(self._background, VideoLoop):
            self._background.stop()
            self._background = None

        if self._output is not None:
            self._output.stop()
            self._output = None

        if self._segmenter is not None:
            self._segmenter.stop()
            self._segmenter = None

        if self._capture is not None:
            self._capture.stop()
            self._capture = None

    def __enter__(self) -> "VirtualCameraPipeline":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


def run_pipeline(config: AppConfig) -> None:
    """Convenience function to run the full pipeline.

    Args:
        config: Application configuration.
    """
    with VirtualCameraPipeline(config) as pipeline:
        pipeline.run()
