"""Performance monitoring utilities."""

import time
from collections import deque
from typing import Optional


class FPSCounter:
    """Track and report frames per second."""

    def __init__(self, window_size: int = 30):
        """Initialize FPS counter.

        Args:
            window_size: Number of frames to average over.
        """
        self._window_size = window_size
        self._timestamps: deque[float] = deque(maxlen=window_size)
        self._last_report_time: float = 0.0
        self._report_interval: float = 1.0

    def tick(self) -> None:
        """Record a frame timestamp."""
        self._timestamps.append(time.perf_counter())

    def get_fps(self) -> float:
        """Calculate current FPS based on recent frames."""
        if len(self._timestamps) < 2:
            return 0.0

        time_span = self._timestamps[-1] - self._timestamps[0]
        if time_span <= 0:
            return 0.0

        return (len(self._timestamps) - 1) / time_span

    def should_report(self) -> bool:
        """Check if enough time has passed for a report."""
        current_time = time.perf_counter()
        if current_time - self._last_report_time >= self._report_interval:
            self._last_report_time = current_time
            return True
        return False

    def get_report(self) -> Optional[str]:
        """Get FPS report if it's time to report."""
        if self.should_report():
            return f"FPS: {self.get_fps():.1f}"
        return None

    def reset(self) -> None:
        """Reset the counter."""
        self._timestamps.clear()
        self._last_report_time = 0.0
