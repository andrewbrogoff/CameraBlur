"""Status panel widget showing pipeline state and FPS."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static


class StatusPanel(Widget):
    """Widget displaying pipeline status and FPS."""

    def __init__(self, **kwargs) -> None:
        """Initialize status panel."""
        super().__init__(**kwargs)
        self._status = "Stopped"
        self._fps = 0.0

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Horizontal(
            Static("Status: ", classes="status-label"),
            Static("Stopped", id="status-text", classes="stopped"),
            Static("   |   FPS: ", classes="status-label"),
            Static("--", id="fps-text"),
        )

    def update_status(self, status: str) -> None:
        """Update the status display.

        Args:
            status: New status text.
        """
        self._status = status
        status_widget = self.query_one("#status-text", Static)
        status_widget.update(status)

        # Update styling based on status
        status_widget.remove_class("running")
        status_widget.remove_class("stopped")
        if status.lower() == "running":
            status_widget.add_class("running")
        else:
            status_widget.add_class("stopped")

    def update_fps(self, fps: float) -> None:
        """Update the FPS display.

        Args:
            fps: Current FPS value.
        """
        self._fps = fps
        fps_text = f"{fps:.1f}" if fps > 0 else "--"
        self.query_one("#fps-text", Static).update(fps_text)

    @property
    def current_status(self) -> str:
        """Get current status."""
        return self._status

    @property
    def current_fps(self) -> float:
        """Get current FPS."""
        return self._fps
