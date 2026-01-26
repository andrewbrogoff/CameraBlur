"""Virtual camera output via pyvirtualcam."""

from typing import Optional

import cv2
import numpy as np
import pyvirtualcam

from ..config import OutputConfig
from ..exceptions import VirtualCameraNotFoundError
from ..utils.system_check import find_virtual_camera


class VirtualCameraOutput:
    """Output frames to a v4l2loopback virtual camera."""

    def __init__(self, config: OutputConfig, width: int, height: int, fps: float):
        """Initialize virtual camera output.

        Args:
            config: Output configuration.
            width: Frame width.
            height: Frame height.
            fps: Target framerate.
        """
        self._config = config
        self._width = width
        self._height = height
        self._fps = fps
        self._cam: Optional[pyvirtualcam.Camera] = None

    def start(self) -> str:
        """Start the virtual camera.

        Returns:
            The device path being used.

        Raises:
            VirtualCameraNotFoundError: If no virtual camera is available.
        """
        device = self._config.device
        if device is None:
            device = find_virtual_camera()
            if device is None:
                raise VirtualCameraNotFoundError(
                    "No v4l2loopback device found. "
                    "Run: sudo modprobe v4l2loopback devices=1 card_label='VirtualCam'"
                )

        self._cam = pyvirtualcam.Camera(
            width=self._width,
            height=self._height,
            fps=self._fps,
            device=device,
            fmt=pyvirtualcam.PixelFormat.BGR,
        )

        return self._cam.device

    def write(self, frame: np.ndarray) -> None:
        """Write a frame to the virtual camera.

        Args:
            frame: BGR frame to output.
        """
        if self._cam is None:
            raise RuntimeError("Virtual camera not started. Call start() first.")

        if frame.shape[1] != self._width or frame.shape[0] != self._height:
            frame = cv2.resize(frame, (self._width, self._height))

        self._cam.send(frame)

    def stop(self) -> None:
        """Stop the virtual camera."""
        if self._cam is not None:
            self._cam.close()
            self._cam = None

    @property
    def device(self) -> Optional[str]:
        """Get the current device path."""
        if self._cam is not None:
            return self._cam.device
        return self._config.device

    def __enter__(self) -> "VirtualCameraOutput":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
