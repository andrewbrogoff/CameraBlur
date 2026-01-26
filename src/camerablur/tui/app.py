"""Main TUI application for CameraBlur."""

import threading
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header

from ..config import AppConfig
from ..pipeline import Command, PipelineCommand, VirtualCameraPipeline
from ..utils.system_check import list_cameras
from .widgets import BackgroundPicker, CameraSelect, EffectControls, StatusPanel


class CameraBlurTUI(App):
    """Interactive TUI for controlling CameraBlur."""

    CSS_PATH = "styles.tcss"
    TITLE = "CameraBlur TUI"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "start_pipeline", "Start"),
        Binding("x", "stop_pipeline", "Stop"),
        Binding("p", "toggle_preview", "Preview"),
        Binding("ctrl+s", "save_config", "Save Config"),
    ]

    def __init__(self, config: AppConfig, config_path: Optional[Path] = None):
        """Initialize the TUI.

        Args:
            config: Application configuration.
            config_path: Path to save configuration to.
        """
        super().__init__()
        self._config = config
        self._config_path = config_path or Path.home() / ".config" / "camerablur" / "config.yaml"
        self._pipeline: Optional[VirtualCameraPipeline] = None
        self._pipeline_thread: Optional[threading.Thread] = None
        self._cameras = list_cameras()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield VerticalScroll(
            CameraSelect(
                cameras=self._cameras,
                selected_id=self._config.camera.device_id,
                id="camera-select",
            ),
            StatusPanel(id="status-panel"),
            EffectControls(
                mode=self._config.effect.mode,
                blur_intensity=self._config.effect.blur_intensity,
                feather_amount=self._config.effect.feather_amount,
                id="effect-controls",
            ),
            BackgroundPicker(
                current_path=self._config.effect.background_path,
                id="background-picker",
            ),
            Horizontal(
                Button("Start", id="start-btn", variant="success"),
                Button("Stop", id="stop-btn", variant="warning", disabled=True),
                Button("Save Config", id="save-btn", variant="primary"),
                Button("Quit", id="quit-btn", variant="error"),
                id="button-bar",
            ),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.query_one(StatusPanel).update_status("Stopped")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "start-btn":
            self.action_start_pipeline()
        elif button_id == "stop-btn":
            self.action_stop_pipeline()
        elif button_id == "save-btn":
            self.action_save_config()
        elif button_id == "quit-btn":
            self.action_quit()

    def action_start_pipeline(self) -> None:
        """Start the camera pipeline."""
        if self._pipeline_thread and self._pipeline_thread.is_alive():
            self.notify("Pipeline already running", severity="warning")
            return

        # Update config from current UI state
        camera_select = self.query_one(CameraSelect)
        effect_controls = self.query_one(EffectControls)
        background_picker = self.query_one(BackgroundPicker)

        self._config.camera.device_id = camera_select.selected_camera_id
        self._config.effect.mode = effect_controls.current_mode
        self._config.effect.blur_intensity = effect_controls.current_blur
        self._config.effect.feather_amount = effect_controls.current_feather
        self._config.effect.background_path = background_picker.current_path

        # Disable print output since we have TUI
        self._pipeline = VirtualCameraPipeline(self._config)
        self._pipeline._print_fps = False
        self._pipeline.set_fps_callback(self._on_fps_update)

        def run_pipeline():
            try:
                with self._pipeline:
                    self._pipeline.run()
            except Exception as e:
                self.call_from_thread(self._on_pipeline_error, str(e))
            finally:
                self.call_from_thread(self._on_pipeline_stopped)

        self._pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
        self._pipeline_thread.start()

        self.query_one("#start-btn", Button).disabled = True
        self.query_one("#stop-btn", Button).disabled = False
        self.query_one(CameraSelect).disabled = True
        self.query_one(StatusPanel).update_status("Running")
        self.notify("Pipeline started")

    def action_stop_pipeline(self) -> None:
        """Stop the camera pipeline."""
        if self._pipeline:
            self._pipeline.request_stop()
            self.query_one(StatusPanel).update_status("Stopping...")

    def _on_pipeline_stopped(self) -> None:
        """Called when pipeline stops."""
        self.query_one("#start-btn", Button).disabled = False
        self.query_one("#stop-btn", Button).disabled = True
        self.query_one(CameraSelect).disabled = False
        self.query_one(StatusPanel).update_status("Stopped")
        self.query_one(StatusPanel).update_fps(0.0)
        self._pipeline = None
        self._pipeline_thread = None

    def _on_pipeline_error(self, error: str) -> None:
        """Called when pipeline encounters an error."""
        self.notify(f"Pipeline error: {error}", severity="error")

    def _on_fps_update(self, fps: float) -> None:
        """Called from pipeline thread with FPS update."""
        self.call_from_thread(self._update_fps_display, fps)

    def _update_fps_display(self, fps: float) -> None:
        """Update FPS display on main thread."""
        self.query_one(StatusPanel).update_fps(fps)

    def action_toggle_preview(self) -> None:
        """Toggle the OpenCV preview window."""
        self._config.debug.preview_window = not self._config.debug.preview_window
        state = "enabled" if self._config.debug.preview_window else "disabled"
        self.notify(f"Preview window {state} (applies on next start)")

    def action_save_config(self) -> None:
        """Save current configuration to file."""
        # Update config from UI
        camera_select = self.query_one(CameraSelect)
        effect_controls = self.query_one(EffectControls)
        background_picker = self.query_one(BackgroundPicker)

        self._config.camera.device_id = camera_select.selected_camera_id
        self._config.effect.mode = effect_controls.current_mode
        self._config.effect.blur_intensity = effect_controls.current_blur
        self._config.effect.feather_amount = effect_controls.current_feather
        self._config.effect.background_path = background_picker.current_path

        # Ensure directory exists
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config.to_yaml(self._config_path)
        self.notify(f"Config saved to {self._config_path}")

    def on_camera_select_changed(self, event: "CameraSelect.Changed") -> None:
        """Handle camera selection change."""
        self._config.camera.device_id = event.camera_id

    def on_effect_controls_blur_changed(self, event: "EffectControls.BlurChanged") -> None:
        """Handle blur intensity change."""
        if self._pipeline:
            self._pipeline.queue_command(
                Command(PipelineCommand.SET_BLUR_INTENSITY, event.value)
            )

    def on_effect_controls_feather_changed(self, event: "EffectControls.FeatherChanged") -> None:
        """Handle feather amount change."""
        if self._pipeline:
            self._pipeline.queue_command(
                Command(PipelineCommand.SET_FEATHER_AMOUNT, event.value)
            )

    def on_effect_controls_mode_changed(self, event: "EffectControls.ModeChanged") -> None:
        """Handle effect mode change."""
        if self._pipeline:
            self._pipeline.queue_command(
                Command(PipelineCommand.SET_EFFECT_MODE, event.mode)
            )

    def on_background_picker_changed(self, event: "BackgroundPicker.Changed") -> None:
        """Handle background path change."""
        if self._pipeline:
            self._pipeline.queue_command(
                Command(PipelineCommand.SET_BACKGROUND, event.path)
            )

    async def action_quit(self) -> None:
        """Quit the application."""
        if self._pipeline:
            self._pipeline.request_stop()
            # Wait briefly for pipeline to stop
            if self._pipeline_thread:
                self._pipeline_thread.join(timeout=2.0)
        self.exit()
