"""Threaded camera capture with frame dropping."""

import threading
from typing import Optional

import cv2
import numpy as np

from ..config import CameraConfig
from ..exceptions import CameraNotFoundError, CameraOpenError


class CameraCapture:
    """Threaded camera capture that drops old frames for freshness."""

    def __init__(self, config: CameraConfig):
        """Initialize camera capture.

        Args:
            config: Camera configuration.
        """
        self._config = config
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the camera capture thread."""
        self._cap = cv2.VideoCapture(self._config.device_id)
        if not self._cap.isOpened():
            raise CameraOpenError(
                f"Failed to open camera device {self._config.device_id}"
            )

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.height)
        self._cap.set(cv2.CAP_PROP_FPS, self._config.fps)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)

        if actual_width != self._config.width or actual_height != self._config.height:
            pass

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self) -> None:
        """Continuously capture frames in background thread."""
        while self._running:
            if self._cap is None:
                break

            ret, frame = self._cap.read()
            if ret:
                with self._frame_lock:
                    self._frame = frame

    def read(self) -> Optional[np.ndarray]:
        """Get the most recent frame.

        Returns:
            The latest frame or None if not available.
        """
        with self._frame_lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def get_frame_size(self) -> tuple[int, int]:
        """Get the actual frame dimensions.

        Returns:
            Tuple of (width, height).
        """
        if self._cap is None:
            return (self._config.width, self._config.height)
        return (
            int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )

    def stop(self) -> None:
        """Stop the capture thread and release resources."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._frame = None

    def __enter__(self) -> "CameraCapture":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
