"""Background image and video loader."""

from enum import Enum
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from ..exceptions import BackgroundNotFoundError, UnsupportedBackgroundError
from .video_loop import VideoLoop


class BackgroundType(Enum):
    """Type of background source."""
    IMAGE = "image"
    VIDEO = "video"


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".avi", ".mkv", ".mov", ".m4v"}


def detect_background_type(path: Path) -> BackgroundType:
    """Detect whether a file is an image or video.

    Args:
        path: Path to the background file.

    Returns:
        BackgroundType indicating file type.

    Raises:
        UnsupportedBackgroundError: If file type is not supported.
    """
    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return BackgroundType.IMAGE
    elif suffix in VIDEO_EXTENSIONS:
        return BackgroundType.VIDEO
    else:
        raise UnsupportedBackgroundError(
            f"Unsupported background format: {suffix}. "
            f"Supported images: {', '.join(IMAGE_EXTENSIONS)}. "
            f"Supported videos: {', '.join(VIDEO_EXTENSIONS)}."
        )


class ImageBackground:
    """Static image background source."""

    def __init__(self, image: np.ndarray):
        """Initialize with a loaded image.

        Args:
            image: BGR image array.
        """
        self._original = image
        self._cached: Optional[np.ndarray] = None
        self._cached_size: tuple[int, int] = (0, 0)

    def get_frame(self, width: int, height: int) -> np.ndarray:
        """Get the background image scaled to target dimensions.

        Args:
            width: Target width.
            height: Target height.

        Returns:
            Scaled BGR image.
        """
        if self._cached is not None and self._cached_size == (width, height):
            return self._cached

        self._cached = cv2.resize(self._original, (width, height))
        self._cached_size = (width, height)
        return self._cached


def load_background(
    path: Path,
) -> Union[ImageBackground, VideoLoop]:
    """Load a background from file.

    Args:
        path: Path to image or video file.

    Returns:
        ImageBackground or VideoLoop instance.

    Raises:
        BackgroundNotFoundError: If file doesn't exist.
        UnsupportedBackgroundError: If file type is not supported.
    """
    if not path.exists():
        raise BackgroundNotFoundError(f"Background file not found: {path}")

    bg_type = detect_background_type(path)

    if bg_type == BackgroundType.IMAGE:
        image = cv2.imread(str(path))
        if image is None:
            raise BackgroundNotFoundError(f"Failed to load image: {path}")
        return ImageBackground(image)

    else:
        video_loop = VideoLoop(path)
        video_loop.start()
        return video_loop
