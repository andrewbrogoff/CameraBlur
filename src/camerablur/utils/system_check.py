"""System checks for v4l2loopback and camera detection."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2


@dataclass
class CameraInfo:
    """Information about a camera device."""
    device_id: int
    device_path: str
    name: str
    is_virtual: bool


def check_v4l2loopback() -> bool:
    """Check if v4l2loopback kernel module is loaded."""
    try:
        result = subprocess.run(
            ["lsmod"],
            capture_output=True,
            text=True,
            check=True,
        )
        return "v4l2loopback" in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_v4l2loopback_devices() -> list[str]:
    """Get list of v4l2loopback virtual camera devices."""
    devices = []
    video_dir = Path("/dev")

    for video_dev in sorted(video_dir.glob("video*")):
        sys_path = Path(f"/sys/devices/virtual/video4linux/{video_dev.name}")
        if sys_path.exists():
            devices.append(str(video_dev))

    return devices


def find_virtual_camera() -> Optional[str]:
    """Find the first available v4l2loopback device."""
    devices = get_v4l2loopback_devices()
    return devices[0] if devices else None


def get_camera_name(device_path: str) -> str:
    """Get the name of a camera device."""
    device_name = Path(device_path).name
    name_path = Path(f"/sys/class/video4linux/{device_name}/name")

    if name_path.exists():
        return name_path.read_text().strip()
    return device_name


def is_virtual_device(device_path: str) -> bool:
    """Check if a device is a virtual camera."""
    device_name = Path(device_path).name
    sys_path = Path(f"/sys/devices/virtual/video4linux/{device_name}")
    return sys_path.exists()


def is_capture_device(device_path: str) -> bool:
    """Check if a device supports video capture using v4l2 capabilities.

    Some webcams create multiple device nodes (video + metadata).
    This checks if the device has the VIDEO_CAPTURE capability.
    """
    import fcntl
    import struct

    # V4L2 constants
    VIDIOC_QUERYCAP = 0x80685600
    V4L2_CAP_VIDEO_CAPTURE = 0x00000001

    try:
        with open(device_path, 'rb') as f:
            # Query capabilities - struct v4l2_capability is 104 bytes
            buf = bytearray(104)
            fcntl.ioctl(f.fileno(), VIDIOC_QUERYCAP, buf)
            # capabilities field is at offset 84, 4 bytes
            capabilities = struct.unpack_from('<I', buf, 84)[0]
            return bool(capabilities & V4L2_CAP_VIDEO_CAPTURE)
    except (OSError, IOError):
        return False


def list_cameras(suppress_warnings: bool = True) -> list[CameraInfo]:
    """List all available camera devices.

    Args:
        suppress_warnings: If True, suppress OpenCV warnings during enumeration.
    """
    import os
    import sys

    cameras = []
    video_dir = Path("/dev")

    # Suppress OpenCV warnings by redirecting stderr file descriptor
    # OpenCV writes to C-level stderr, so we need to redirect fd 2
    old_stderr_fd = None
    devnull_fd = None
    if suppress_warnings:
        old_stderr_fd = os.dup(2)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, 2)

    try:
        for video_dev in sorted(video_dir.glob("video*")):
            device_path = str(video_dev)
            device_id = int(video_dev.name.replace("video", ""))

            # Check if it's a virtual device first - don't try to open output-only devices
            is_virtual = is_virtual_device(device_path)
            if is_virtual:
                # Still add virtual devices to the list but don't try to open them
                name = get_camera_name(device_path)
                cameras.append(CameraInfo(
                    device_id=device_id,
                    device_path=device_path,
                    name=name,
                    is_virtual=True,
                ))
                continue

            # Check if this is actually a capture device (not metadata node)
            if not is_capture_device(device_path):
                continue

            # Try to open physical cameras and verify we can read from them
            cap = cv2.VideoCapture(device_id)
            if cap.isOpened():
                # Try to read a frame to verify the device actually works
                ret, _ = cap.read()
                if ret:
                    name = get_camera_name(device_path)
                    cameras.append(CameraInfo(
                        device_id=device_id,
                        device_path=device_path,
                        name=name,
                        is_virtual=False,
                    ))
                cap.release()
    finally:
        if suppress_warnings and old_stderr_fd is not None:
            os.dup2(old_stderr_fd, 2)
            os.close(old_stderr_fd)
            if devnull_fd is not None:
                os.close(devnull_fd)

    return cameras


def get_real_cameras() -> list[CameraInfo]:
    """Get list of real (non-virtual) camera devices."""
    return [cam for cam in list_cameras() if not cam.is_virtual]


def check_system_requirements() -> dict[str, bool]:
    """Check all system requirements and return status."""
    return {
        "v4l2loopback_loaded": check_v4l2loopback(),
        "virtual_camera_available": find_virtual_camera() is not None,
        "real_camera_available": len(get_real_cameras()) > 0,
    }
