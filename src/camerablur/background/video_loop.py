"""Looping video background with threaded reading."""

import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from ..exceptions import BackgroundError


class VideoLoop:
    """Threaded looping video background source."""

    def __init__(self, path: Path, buffer_size: int = 5):
        """Initialize video loop.

        Args:
            path: Path to video file.
            buffer_size: Number of frames to preload.
        """
        self._path = path
        self._buffer_size = buffer_size
        self._cap: Optional[cv2.VideoCapture] = None
        self._current_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._fps: float = 30.0
        self._frame_duration: float = 1.0 / 30.0
        self._cached_frame: Optional[np.ndarray] = None
        self._cached_size: tuple[int, int] = (0, 0)

    def start(self) -> None:
        """Start the video loop thread."""
        self._cap = cv2.VideoCapture(str(self._path))
        if not self._cap.isOpened():
            raise BackgroundError(f"Failed to open video: {self._path}")

        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._frame_duration = 1.0 / self._fps

        ret, frame = self._cap.read()
        if ret:
            with self._frame_lock:
                self._current_frame = frame

        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        """Continuously read frames from video in background."""
        last_frame_time = time.perf_counter()

        while self._running:
            if self._cap is None:
                break

            current_time = time.perf_counter()
            elapsed = current_time - last_frame_time

            if elapsed < self._frame_duration:
                time.sleep(self._frame_duration - elapsed)

            ret, frame = self._cap.read()

            if not ret:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()
                if not ret:
                    continue

            with self._frame_lock:
                self._current_frame = frame

            last_frame_time = time.perf_counter()

    def get_frame(self, width: int, height: int) -> Optional[np.ndarray]:
        """Get the current video frame scaled to target dimensions.

        Args:
            width: Target width.
            height: Target height.

        Returns:
            Scaled BGR frame or None if not available.
        """
        with self._frame_lock:
            if self._current_frame is None:
                return None

            if self._cached_size == (width, height) and self._cached_frame is not None:
                if np.array_equal(self._cached_frame, self._current_frame):
                    return self._cached_frame

            frame = cv2.resize(self._current_frame, (width, height))
            self._cached_frame = frame
            self._cached_size = (width, height)
            return frame

    def stop(self) -> None:
        """Stop the video loop thread and release resources."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._current_frame = None
        self._cached_frame = None

    def __enter__(self) -> "VideoLoop":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
