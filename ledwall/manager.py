from PIL import Image

import settings

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

    def describe(self, names):
        """Name, label and icon of the given screens (for the phone page)."""
        out = []
        for n in names:
            if n in self._screens:
                screen = self._screens[n]
                item = {"name": n, "label": screen.label, "icon": screen.icon}
                if screen.page:
                    item["page"] = screen.page
                out.append(item)
        return out

    def set_active(self, name: str) -> None:
        if name not in self._screens:
            raise KeyError(f"unknown screen: {name}")
        self._active = name

    @property
    def fps(self):
        """How often the active screen should be redrawn."""
        return self._screens[self._active].fps or settings.FPS

    def render(self, now: float) -> Image.Image:
        return self._screens[self._active].render(now)
