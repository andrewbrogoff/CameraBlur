"""Effect controls widget with inputs and mode selection."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select, Static

from ...config import EffectMode


class EffectControls(Widget):
    """Widget for controlling blur, feather, and effect mode."""

    class BlurChanged(Message):
        """Message sent when blur intensity changes."""

        def __init__(self, value: int) -> None:
            self.value = value
            super().__init__()

    class FeatherChanged(Message):
        """Message sent when feather amount changes."""

        def __init__(self, value: int) -> None:
            self.value = value
            super().__init__()

    class ModeChanged(Message):
        """Message sent when effect mode changes."""

        def __init__(self, mode: EffectMode) -> None:
            self.mode = mode
            super().__init__()

    def __init__(
        self,
        mode: EffectMode = EffectMode.BLUR,
        blur_intensity: int = 21,
        feather_amount: int = 3,
        **kwargs,
    ) -> None:
        """Initialize effect controls.

        Args:
            mode: Initial effect mode.
            blur_intensity: Initial blur intensity.
            feather_amount: Initial feather amount.
        """
        super().__init__(**kwargs)
        self._mode = mode
        self._blur = blur_intensity
        self._feather = feather_amount

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Effect Settings", classes="section-title")

        # Effect mode selector
        yield Horizontal(
            Label("Mode: "),
            Select(
                options=[
                    ("Blur", EffectMode.BLUR),
                    ("Image", EffectMode.IMAGE),
                    ("Video", EffectMode.VIDEO),
                    ("None", EffectMode.NONE),
                ],
                value=self._mode,
                id="mode-select",
            ),
            classes="control-row",
        )

        # Blur intensity control
        yield Horizontal(
            Label("Blur Intensity (1-101): "),
            Button("-", id="blur-dec", classes="small-btn"),
            Input(
                value=str(self._blur),
                id="blur-input",
                type="integer",
            ),
            Button("+", id="blur-inc", classes="small-btn"),
            classes="control-row",
        )

        # Feather amount control
        yield Horizontal(
            Label("Feather Amount (0-20): "),
            Button("-", id="feather-dec", classes="small-btn"),
            Input(
                value=str(self._feather),
                id="feather-input",
                type="integer",
            ),
            Button("+", id="feather-inc", classes="small-btn"),
            classes="control-row",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "blur-dec":
            self._adjust_blur(-2)
        elif button_id == "blur-inc":
            self._adjust_blur(2)
        elif button_id == "feather-dec":
            self._adjust_feather(-1)
        elif button_id == "feather-inc":
            self._adjust_feather(1)

    def _adjust_blur(self, delta: int) -> None:
        """Adjust blur intensity."""
        new_value = self._blur + delta
        new_value = max(1, min(101, new_value))
        # Ensure odd
        if new_value % 2 == 0:
            new_value += 1 if delta > 0 else -1
        new_value = max(1, min(101, new_value))

        if new_value != self._blur:
            self._blur = new_value
            self.query_one("#blur-input", Input).value = str(new_value)
            self.post_message(self.BlurChanged(new_value))

    def _adjust_feather(self, delta: int) -> None:
        """Adjust feather amount."""
        new_value = self._feather + delta
        new_value = max(0, min(20, new_value))

        if new_value != self._feather:
            self._feather = new_value
            self.query_one("#feather-input", Input).value = str(new_value)
            self.post_message(self.FeatherChanged(new_value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        input_id = event.input.id
        try:
            value = int(event.value)
        except ValueError:
            return

        if input_id == "blur-input":
            value = max(1, min(101, value))
            if value % 2 == 0:
                value += 1
            self._blur = value
            event.input.value = str(value)
            self.post_message(self.BlurChanged(value))

        elif input_id == "feather-input":
            value = max(0, min(20, value))
            self._feather = value
            event.input.value = str(value)
            self.post_message(self.FeatherChanged(value))

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle mode selection change."""
        if event.select.id == "mode-select" and event.value is not None:
            self._mode = event.value
            self.post_message(self.ModeChanged(event.value))

    @property
    def current_mode(self) -> EffectMode:
        """Get current effect mode."""
        return self._mode

    @property
    def current_blur(self) -> int:
        """Get current blur intensity."""
        return self._blur

    @property
    def current_feather(self) -> int:
        """Get current feather amount."""
        return self._feather
