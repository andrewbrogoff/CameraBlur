"""Camera selection widget."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Select, Static

from ...utils.system_check import CameraInfo


class CameraSelect(Widget):
    """Widget for selecting camera device."""

    class Changed(Message):
        """Message sent when camera selection changes."""

        def __init__(self, camera_id: int) -> None:
            self.camera_id = camera_id
            super().__init__()

    def __init__(
        self,
        cameras: list[CameraInfo],
        selected_id: int = 0,
        **kwargs,
    ) -> None:
        """Initialize camera select widget.

        Args:
            cameras: List of available cameras.
            selected_id: Initially selected camera ID.
        """
        super().__init__(**kwargs)
        self._cameras = cameras
        self._selected_id = selected_id
        # Filter to only show physical cameras for input
        self._input_cameras = [c for c in cameras if not c.is_virtual]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Camera Source", classes="label")
        if self._input_cameras:
            options = [
                (f"{cam.name} ({cam.device_path})", cam.device_id)
                for cam in self._input_cameras
            ]
            # Find the value to select
            selected_value = self._selected_id
            if not any(cam.device_id == selected_value for cam in self._input_cameras):
                selected_value = self._input_cameras[0].device_id

            yield Select(
                options=options,
                value=selected_value,
                id="camera-dropdown",
            )
        else:
            yield Static("[red]No physical cameras found[/red]")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selection change."""
        if event.value is not None:
            self._selected_id = event.value
            self.post_message(self.Changed(event.value))

    @property
    def selected_camera_id(self) -> int:
        """Get currently selected camera ID."""
        return self._selected_id

    @property
    def disabled(self) -> bool:
        """Check if widget is disabled."""
        try:
            select = self.query_one("#camera-dropdown", Select)
            return select.disabled
        except Exception:
            return False

    @disabled.setter
    def disabled(self, value: bool) -> None:
        """Set widget disabled state."""
        try:
            select = self.query_one("#camera-dropdown", Select)
            select.disabled = value
        except Exception:
            pass
