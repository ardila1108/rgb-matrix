from abc import ABC, abstractmethod

from PIL import Image


class Screen(ABC):
    """One thing the panel can show (buses, weather, now playing, ...).

    A screen owns its own data and drawing. It never talks to the hardware:
    it hands back a PIL image and the backend puts it on the panel.
    """

    #: short unique id used by the ScreenManager, e.g. "bus"
    name: str = "screen"
    #: how the screen is called on the phone page
    label: str = "Screen"
    icon: str = "▫️"

    @abstractmethod
    def update(self, data) -> None:
        """Receive fresh data. Called from another thread, must be thread-safe."""

    @abstractmethod
    def render(self, now: float) -> Image.Image:
        """Return the current frame (RGB, COLS x ROWS). `now` is time.monotonic()."""
