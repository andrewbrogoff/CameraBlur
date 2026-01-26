"""Background blur and replacement effects."""

from typing import Optional, Protocol

import cv2
import numpy as np

from ..config import EffectConfig, EffectMode


class BackgroundSource(Protocol):
    """Protocol for background frame sources."""

    def get_frame(self, width: int, height: int) -> Optional[np.ndarray]:
        """Get a background frame scaled to the specified dimensions."""
        ...


class EffectsProcessor:
    """Apply blur or replacement effects using segmentation mask."""

    def __init__(self, config: EffectConfig):
        """Initialize effects processor.

        Args:
            config: Effect configuration.
        """
        self._config = config
        self._background_source: Optional[BackgroundSource] = None
        self._cached_background: Optional[np.ndarray] = None
        self._cached_size: tuple[int, int] = (0, 0)

    def set_background_source(self, source: Optional[BackgroundSource]) -> None:
        """Set the background source for image/video replacement.

        Args:
            source: Background frame source or None for blur mode.
        """
        self._background_source = source
        self._cached_background = None

    def process(
        self,
        frame: np.ndarray,
        mask: np.ndarray,
    ) -> np.ndarray:
        """Apply effect to frame using segmentation mask.

        Args:
            frame: BGR input frame.
            mask: Single-channel mask (0-255) where 255 = person.

        Returns:
            Processed BGR frame.
        """
        if self._config.mode == EffectMode.NONE:
            return frame

        height, width = frame.shape[:2]

        if self._config.feather_amount > 0:
            kernel_size = self._config.feather_amount * 2 + 1
            mask = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)

        mask_float = mask.astype(np.float32) / 255.0
        mask_3ch = np.stack([mask_float] * 3, axis=-1)

        background = self._get_background(frame, width, height)

        result = (frame * mask_3ch + background * (1 - mask_3ch)).astype(np.uint8)

        return result

    def _get_background(
        self,
        frame: np.ndarray,
        width: int,
        height: int,
    ) -> np.ndarray:
        """Get the background for compositing.

        Args:
            frame: Original frame (used for blur mode).
            width: Target width.
            height: Target height.

        Returns:
            Background BGR frame.
        """
        if self._config.mode == EffectMode.BLUR:
            return cv2.GaussianBlur(
                frame,
                (self._config.blur_intensity, self._config.blur_intensity),
                0,
            )

        if self._config.mode in (EffectMode.IMAGE, EffectMode.VIDEO):
            if self._background_source is not None:
                bg_frame = self._background_source.get_frame(width, height)
                if bg_frame is not None:
                    return bg_frame

        return cv2.GaussianBlur(
            frame,
            (self._config.blur_intensity, self._config.blur_intensity),
            0,
        )

    def update_blur_intensity(self, intensity: int) -> None:
        """Update blur intensity at runtime.

        Args:
            intensity: New blur kernel size (will be made odd).
        """
        if intensity % 2 == 0:
            intensity += 1
        self._config.blur_intensity = intensity

    def update_feather_amount(self, amount: int) -> None:
        """Update edge feathering at runtime.

        Args:
            amount: Feather amount in pixels.
        """
        self._config.feather_amount = max(0, min(20, amount))

    def update_mode(self, mode: EffectMode) -> None:
        """Update effect mode at runtime.

        Args:
            mode: New effect mode.
        """
        self._config.mode = mode
