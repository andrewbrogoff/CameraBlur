"""Custom exceptions for CameraBlur."""


class CameraBlurError(Exception):
    """Base exception for CameraBlur errors."""


class CameraError(CameraBlurError):
    """Error related to camera capture."""


class CameraNotFoundError(CameraError):
    """Camera device not found."""


class CameraOpenError(CameraError):
    """Failed to open camera device."""


class VirtualCameraError(CameraBlurError):
    """Error related to virtual camera output."""


class V4L2LoopbackNotFoundError(VirtualCameraError):
    """v4l2loopback kernel module not loaded."""


class VirtualCameraNotFoundError(VirtualCameraError):
    """No virtual camera device available."""


class SegmentationError(CameraBlurError):
    """Error in segmentation processing."""


class BackgroundError(CameraBlurError):
    """Error loading or processing background."""


class BackgroundNotFoundError(BackgroundError):
    """Background file not found."""


class UnsupportedBackgroundError(BackgroundError):
    """Unsupported background file format."""


class ConfigurationError(CameraBlurError):
    """Error in configuration."""
