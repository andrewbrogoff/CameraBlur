"""Pydantic configuration models for CameraBlur."""

from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class SegmentationModel(str, Enum):
    """Available MediaPipe segmentation model types."""
    GENERAL = "general"
    LANDSCAPE = "landscape"


class RVMModel(str, Enum):
    """Available RVM (Robust Video Matting) model variants."""
    MOBILENETV3 = "mobilenetv3"  # Fast (~30 FPS @ 1080p)
    RESNET50 = "resnet50"        # High quality (~15 FPS @ 1080p)


class SegmentationBackend(str, Enum):
    """Available segmentation backends."""
    RVM = "rvm"              # GPU-accelerated (default)
    MEDIAPIPE = "mediapipe"  # Legacy CPU fallback


class EffectMode(str, Enum):
    """Available effect modes."""
    BLUR = "blur"
    IMAGE = "image"
    VIDEO = "video"
    NONE = "none"


class CameraConfig(BaseModel):
    """Camera input configuration."""
    device_id: int = Field(default=0, ge=0, description="Camera device ID")
    width: int = Field(default=1920, gt=0, description="Capture width")
    height: int = Field(default=1080, gt=0, description="Capture height")
    fps: int = Field(default=30, gt=0, le=120, description="Target FPS")


class SegmentationConfig(BaseModel):
    """Segmentation model configuration."""
    backend: SegmentationBackend = Field(
        default=SegmentationBackend.RVM,
        description="Segmentation backend (rvm for GPU, mediapipe for CPU)"
    )
    # RVM-specific options
    rvm_model: RVMModel = Field(
        default=RVMModel.MOBILENETV3,
        description="RVM model variant"
    )
    downsample_ratio: float = Field(
        default=0.25,
        ge=0.1,
        le=1.0,
        description="RVM downsample ratio (lower = faster, 0.1-1.0)"
    )
    # MediaPipe-specific options (legacy)
    model: SegmentationModel = Field(
        default=SegmentationModel.LANDSCAPE,
        description="MediaPipe segmentation model type"
    )
    smoothing: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Temporal smoothing frames (MediaPipe only)"
    )
    # Common options
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Segmentation threshold"
    )


class EffectConfig(BaseModel):
    """Effect configuration."""
    mode: EffectMode = Field(default=EffectMode.BLUR, description="Effect mode")
    blur_intensity: int = Field(
        default=21,
        ge=1,
        description="Blur kernel size (must be odd)"
    )
    feather_amount: int = Field(
        default=3,
        ge=0,
        le=20,
        description="Edge feathering amount"
    )
    background_path: Optional[Path] = Field(
        default=None,
        description="Path to background image or video"
    )

    @field_validator("blur_intensity")
    @classmethod
    def blur_must_be_odd(cls, v: int) -> int:
        """Ensure blur intensity is odd for OpenCV."""
        if v % 2 == 0:
            return v + 1
        return v


class OutputConfig(BaseModel):
    """Virtual camera output configuration."""
    device: Optional[str] = Field(
        default=None,
        description="Virtual camera device path (auto-detect if None)"
    )


class DebugConfig(BaseModel):
    """Debug and development configuration."""
    preview_window: bool = Field(
        default=False,
        description="Show preview window"
    )


class AppConfig(BaseModel):
    """Main application configuration."""
    camera: CameraConfig = Field(default_factory=CameraConfig)
    segmentation: SegmentationConfig = Field(default_factory=SegmentationConfig)
    effect: EffectConfig = Field(default_factory=EffectConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "AppConfig":
        """Load configuration from a YAML file."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls.model_validate(data)

    def to_yaml(self, path: Path) -> None:
        """Save configuration to a YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.model_dump(mode="json"), f, default_flow_style=False)


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from file or return defaults.

    Searches for config in:
    1. Provided path
    2. ./config.yaml
    3. ~/.config/camerablur/config.yaml
    """
    search_paths = []
    if config_path:
        search_paths.append(config_path)
    search_paths.extend([
        Path("config.yaml"),
        Path.home() / ".config" / "camerablur" / "config.yaml",
    ])

    for path in search_paths:
        if path.exists():
            return AppConfig.from_yaml(path)

    return AppConfig()
