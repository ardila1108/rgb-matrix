"""Halloween screen: a little night show of pumpkins, ghosts, bats and a dancing skeleton.

It plays four short acts one after the other (settings.HALLOWEEN_ACT_SECONDS each). Every
time the screen comes back after being away it starts with the next act, so a rotation
never shows the same thing twice in a row.
"""
import math

from PIL import ImageDraw

import settings
from .. import font, halloween_art as art
from .base import Screen


class HalloweenScreen(Screen):
    name = "halloween"
    label = "Halloween"
    icon = "🎃"
    fps = 10

    def __init__(self):
        self._acts = [self._title, self._patch, self._graveyard, self._haunted_moon]
        self._act = 0
        self._act_start = 0.0
        self._last = None

    def update(self, data=None):
        pass                                       # nothing to feed it

    def render(self, now):
        seconds = max(float(settings.HALLOWEEN_ACT_SECONDS), 3.0)
        if self._last is None:
            self._act, self._act_start = 0, now
        elif now - self._last > 1.0 or now - self._act_start >= seconds:
            # coming back after a while, or the act is over: the next act starts from its beginning
            self._act, self._act_start = (self._act + 1) % len(self._acts), now
        self._last = now

        img = art.sky()
        d = ImageDraw.Draw(img)
        tick = int(now * 4)
        art.stars(d, tick)
        self._acts[self._act](d, now - self._act_start, tick)
        return img

    @property
    def act(self):
        return self._act

    # -- acts ------------------------------------------------------------------------
    def _title(self, d, t, tick):
        """HAPPY HALLOWEEN, letter by letter, then a pumpkin pops up and ghosts drift in."""
        letters = min(5, int(t / 0.3) + 1)
        font.draw_text(d, "HAPPY"[:letters], 3, 4, art.GLOW_D if tick % 6 == 0 else art.GLOW, sx=2, sy=2)
        shown = max(0, min(9, int((t - 1.8) / 0.15) + 1))
        font.draw_text(d, "HALLOWEEN"[:shown], 5, 23, art.PURPLE_TEXT)

        art.ghost(d, 9, 42 + round(2 * math.sin(t * 2)), 0.8 * art.clamp(t - 3.5) * (0.75 + 0.25 * math.sin(t * 3)))
        art.ghost(d, 55, 40 + round(2 * math.sin(t * 2 + 2)), 0.8 * art.clamp(t - 4.2) * (0.75 + 0.25 * math.sin(t * 3 + 1)))
        if t > 5:
            art.bat(d, int(-6 + (t - 5) / 4.5 * 76), 36 + round(3 * math.sin(t * 3)), int(t * 6))
        art.ground(d)
        art.pumpkin(d, 32, 50, art.clamp((t - 2.8) / 0.6), tick)

    def _patch(self, d, t, tick):
        """Pumpkins pop up one by one while a ghost glides past and eyes blink in the dark."""
        art.moon(d, 50, 12, 6)
        if t > 3 and (t - 3) % 2.5 > 0.2:
            art.eyes(d, 6, 32, art.EYES_YELLOW)
        if t > 5 and (t - 5) % 3.1 > 0.2:
            art.eyes(d, 52, 27, art.EYES_GREEN)
        glide = (t - 1.5) / 7
        if 0 <= glide <= 1:
            art.ghost(d, int(-8 + glide * 80), 22 + round(3 * math.sin(t * 2)), 0.9 * math.sin(math.pi * glide))
        art.ground(d)
        art.pumpkin(d, 13, 54, art.clamp((t - 1.6) / 0.6), tick, small=True, seed=1)
        art.pumpkin(d, 51, 54, art.clamp((t - 2.6) / 0.6), tick, small=True, seed=2)
        art.pumpkin(d, 32, 50, art.clamp((t - 0.6) / 0.6), tick)

    def _graveyard(self, d, t, tick):
        """A skeleton climbs out of the ground and dances between the tombstones."""
        art.moon(d, 14, 12, 7)
        if t > 3:
            art.bat(d, int(70 - (t - 3) / 6 * 80), 30 + round(4 * math.sin(t * 2)), int(t * 6))
        if t > 5:
            art.ghost(d, 57, 24 + round(2 * math.sin(t * 2)), 0.8 * art.clamp((t - 5) / 1.5))
        art.tombstone(d, 3, 9, 13)
        art.tombstone(d, 19, 8, 10)
        art.tombstone(d, 53, 9, 12)
        rise = art.clamp((t - 0.5) / 1.6)
        art.skeleton(d, 36, int(art.GROUND_Y - 24 + (1 - rise) * 26), int(t * 3) % 2 if rise >= 1 else 0)
        art.ground(d)

    def _haunted_moon(self, d, t, tick):
        """A big moon, bats crossing it, a spider dropping down, and a BOO! at the end."""
        art.moon(d, 44, 18, 12)
        for i, (phase, y0) in enumerate([(0, 10), (30, 26), (55, 16)]):
            x = (t * 9 + phase) % 84 - 10
            art.bat(d, int(x), int(y0 + 3 * math.sin(t * 2 + phase)), int(t * 6 + i))
        art.spider(d, 12, int(8 + 16 * (0.5 - 0.5 * math.cos(t * 0.9))))
        art.ground(d)
        if 6.5 <= t < 9.5:
            shake = (tick % 2) * 2 - 1
            font.draw_text(d, "BOO!", 9 + shake, 36, art.RED if tick % 2 == 0 else art.GLOW_D, sx=2, sy=2)
