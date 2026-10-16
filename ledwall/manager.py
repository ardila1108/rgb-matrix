from PIL import Image

from .screens.base import Screen


class ScreenManager:
    """Holds the available screens and decides which one is on the panel.

    For now it shows one screen: the first, or the one named by `active`. Later this is where switching
    (schedule, button, MQTT, ...) and rotation between screens will live.
    """

    def __init__(self, screens, active=None):
        if not screens:
            raise ValueError("ScreenManager needs at least one screen")
        self._screens = {s.name: s for s in screens}
        self._active = screens[0].name
        if active is not None:
            self.set_active(active)

    @property
    def active(self) -> str:
        return self._active

    def get(self, name: str) -> Screen:
        return self._screens[name]

    def set_active(self, name: str) -> None:
        if name not in self._screens:
            raise KeyError(f"unknown screen: {name}")
        self._active = name

    def render(self, now: float) -> Image.Image:
        return self._screens[self._active].render(now)
