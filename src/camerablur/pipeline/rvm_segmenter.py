"""RVM (Robust Video Matting) segmenter with CUDA support."""

import warnings
from pathlib import Path
from typing import Optional
import urllib.request

import cv2
import numpy as np
import torch

from ..config import RVMModel, SegmentationConfig

# Model URLs for RVM TorchScript models (fp32 variants for better precision)
_MODEL_URLS = {
    RVMModel.MOBILENETV3: "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.torchscript",
    RVMModel.RESNET50: "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_resnet50_fp32.torchscript",
}

_MODEL_FILENAMES = {
    RVMModel.MOBILENETV3: "rvm_mobilenetv3_fp32.torchscript",
    RVMModel.RESNET50: "rvm_resnet50_fp32.torchscript",
}


def _download_file(url: str, dest: Path) -> None:
    """Download a file from URL with proper headers for GitHub."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) CameraBlur/0.1.0",
            "Accept": "application/octet-stream",
        },
    )
    with urllib.request.urlopen(request) as response:
        with open(dest, "wb") as f:
            f.write(response.read())


def _get_model_path(model: RVMModel) -> Path:
    """Get path to model file, downloading if necessary."""
    cache_dir = Path.home() / ".cache" / "camerablur" / "models"
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_path = cache_dir / _MODEL_FILENAMES[model]

    if not model_path.exists():
        url = _MODEL_URLS[model]
        print(f"Downloading RVM model from {url}...")
        _download_file(url, model_path)
        print(f"Model saved to {model_path}")

    return model_path


class RVMSegmenter:
    """Robust Video Matting segmenter with CUDA support.

    Uses RVM's recurrent architecture for temporally consistent segmentation
    without requiring explicit frame averaging like MediaPipe.
    """

    def __init__(self, config: SegmentationConfig):
        """Initialize RVM segmenter.

        Args:
            config: Segmentation configuration.
        """
        self._config = config
        self._model: Optional[torch.jit.ScriptModule] = None
        self._device: Optional[torch.device] = None

        # RVM recurrent state (maintained between frames for temporal consistency)
        self._rec: list[Optional[torch.Tensor]] = [None] * 4
        self._downsample_ratio: Optional[torch.Tensor] = None

    def start(self) -> None:
        """Initialize RVM model and load to appropriate device."""
        # Determine device
        if torch.cuda.is_available():
            self._device = torch.device("cuda")
            print(f"RVM using CUDA: {torch.cuda.get_device_name(0)}")
        else:
            self._device = torch.device("cpu")
            warnings.warn(
                "CUDA not available. RVM falling back to CPU - "
                "performance will be significantly reduced. "
                "Consider using --no-gpu to use MediaPipe instead.",
                stacklevel=2,
            )

        # Load model
        model_path = _get_model_path(self._config.rvm_model)
        self._model = torch.jit.load(str(model_path), map_location=self._device)
        self._model.eval()

        # Pre-compute downsample ratio tensor
        self._downsample_ratio = torch.tensor(
            [self._config.downsample_ratio],
            device=self._device,
        )

        # Reset recurrent state
        self._rec = [None] * 4

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Generate segmentation mask for frame.

        Args:
            frame: BGR input frame.

        Returns:
            Single-channel mask (0-255) where 255 = person.
        """
        if self._model is None:
            raise RuntimeError("RVMSegmenter not started. Call start() first.")

        # Convert BGR to RGB and normalize to [0, 1]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb_frame).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        tensor = tensor.to(self._device)

        # Run inference
        with torch.no_grad():
            fgr, pha, *self._rec = self._model(tensor, *self._rec, self._downsample_ratio)

        # Extract alpha matte and convert to mask
        alpha = pha[0, 0].cpu().numpy()

        # Apply threshold
        mask = (alpha > self._config.threshold).astype(np.float32)

        # Convert to uint8 (0-255)
        mask_uint8 = (mask * 255).astype(np.uint8)

        return mask_uint8

    def stop(self) -> None:
        """Release RVM resources."""
        self._model = None
        self._rec = [None] * 4
        self._downsample_ratio = None

        # Clear CUDA cache if using GPU
        if self._device is not None and self._device.type == "cuda":
            torch.cuda.empty_cache()

        self._device = None

    def __enter__(self) -> "RVMSegmenter":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
