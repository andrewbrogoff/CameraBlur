"""Background file picker widget."""

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Static


class BackgroundPicker(Widget):
    """Widget for selecting background image or video."""

    class Changed(Message):
        """Message sent when background path changes."""

        def __init__(self, path: Optional[Path]) -> None:
            self.path = path
            super().__init__()

    def __init__(
        self,
        current_path: Optional[Path] = None,
        **kwargs,
    ) -> None:
        """Initialize background picker.

        Args:
            current_path: Initial background path.
        """
        super().__init__(**kwargs)
        self._path = current_path

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Background (image or video)", classes="section-title")
        yield Input(
            placeholder="Enter path to background file...",
            value=str(self._path) if self._path else "",
            id="bg-path-input",
        )
        yield Horizontal(
            Button("Apply", id="apply-bg-btn", variant="primary"),
            Button("Clear", id="clear-bg-btn", variant="warning"),
            id="bg-button-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "apply-bg-btn":
            self._apply_background()
        elif event.button.id == "clear-bg-btn":
            self._clear_background()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input."""
        if event.input.id == "bg-path-input":
            self._apply_background()

    def _apply_background(self) -> None:
        """Apply the current input path."""
        input_widget = self.query_one("#bg-path-input", Input)
        path_str = input_widget.value.strip()

        if not path_str:
            self.app.notify("Please enter a file path", severity="warning")
            return

        path = Path(path_str).expanduser()
        if not path.exists():
            self.app.notify(f"File not found: {path}", severity="error")
            return

        # Check if it's a valid image or video
        valid_extensions = {
            ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
            ".mp4", ".avi", ".mkv", ".mov", ".webm",
        }
        if path.suffix.lower() not in valid_extensions:
            self.app.notify(
                f"Unsupported file type: {path.suffix}",
                severity="error"
            )
            return

        self._path = path
        self.post_message(self.Changed(path))
        self.app.notify(f"Background set: {path.name}")

    def _clear_background(self) -> None:
        """Clear the background."""
        self._path = None
        self.query_one("#bg-path-input", Input).value = ""
        self.post_message(self.Changed(None))
        self.app.notify("Background cleared")

    @property
    def current_path(self) -> Optional[Path]:
        """Get current background path."""
        return self._path
