"""MediaPipe selfie segmentation wrapper."""

from collections import deque
from pathlib import Path
from typing import Optional
import urllib.request

import cv2
import mediapipe as mp
import numpy as np

from ..config import SegmentationConfig, SegmentationModel

# Model URLs for MediaPipe Tasks API
_MODEL_URLS = {
    SegmentationModel.GENERAL: "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite",
    SegmentationModel.LANDSCAPE: "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter_landscape/float16/latest/selfie_segmenter_landscape.tflite",
}

_MODEL_FILENAMES = {
    SegmentationModel.GENERAL: "selfie_segmenter.tflite",
    SegmentationModel.LANDSCAPE: "selfie_segmenter_landscape.tflite",
}


def _get_model_path(model: SegmentationModel) -> Path:
    """Get path to model file, downloading if necessary."""
    cache_dir = Path.home() / ".cache" / "camerablur" / "models"
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_path = cache_dir / _MODEL_FILENAMES[model]

    if not model_path.exists():
        url = _MODEL_URLS[model]
        urllib.request.urlretrieve(url, model_path)

    return model_path


class Segmenter:
    """MediaPipe selfie segmentation with temporal smoothing."""

    def __init__(self, config: SegmentationConfig):
        """Initialize segmenter.

        Args:
            config: Segmentation configuration.
        """
        self._config = config
        self._segmenter: Optional[mp.tasks.vision.ImageSegmenter] = None
        self._mask_history: deque[np.ndarray] = deque(maxlen=max(1, config.smoothing))

    def start(self) -> None:
        """Initialize MediaPipe model."""
        model_path = _get_model_path(self._config.model)

        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
        options = mp.tasks.vision.ImageSegmenterOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            output_confidence_masks=True,
            output_category_mask=False,
        )
        self._segmenter = mp.tasks.vision.ImageSegmenter.create_from_options(options)

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Generate segmentation mask for frame.

        Args:
            frame: BGR input frame.

        Returns:
            Single-channel mask (0-255) where 255 = person.
        """
        if self._segmenter is None:
            raise RuntimeError("Segmenter not started. Call start() first.")

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = self._segmenter.segment(mp_image)

        # The selfie segmenter outputs a single mask for person confidence
        mask = result.confidence_masks[0].numpy_view()
        # Remove the extra dimension (H, W, 1) -> (H, W)
        if mask.ndim == 3:
            mask = mask.squeeze(axis=-1)

        mask = (mask > self._config.threshold).astype(np.float32)

        if self._config.smoothing > 0:
            self._mask_history.append(mask)
            if len(self._mask_history) > 1:
                mask = np.mean(self._mask_history, axis=0)

        mask_uint8 = (mask * 255).astype(np.uint8)

        return mask_uint8

    def stop(self) -> None:
        """Release MediaPipe resources."""
        if self._segmenter is not None:
            self._segmenter.close()
            self._segmenter = None
        self._mask_history.clear()

    def __enter__(self) -> "Segmenter":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
