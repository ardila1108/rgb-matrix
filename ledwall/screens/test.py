"""Panel test patterns: check wiring, orientation, colors and power.

Select with LED_SCREEN=test. Cycles through the patterns below.
"""
from PIL import Image, ImageDraw

import settings
from .. import font
from .base import Screen

W, H = 64, 64
BAR_COLORS = [(255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
              (255, 0, 255), (255, 0, 0), (0, 0, 255), (60, 60, 60)]
FILL_COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]


class TestScreen(Screen):
    __test__ = False          # not a pytest class
    name = "test"
    PATTERNS = ("bars", "grid", "scan", "fill")

    def update(self, data=None):
        pass                  # no data needed

    def render(self, now):
        step = max(settings.TEST_SECONDS_PER_PATTERN, 0.5)
        pattern = self.PATTERNS[int(now // step) % len(self.PATTERNS)]
        return getattr(self, "_" + pattern)(now)

    def _bars(self, now):
        """Color bars on top, gray/R/G/B ramps below: color order and gamma."""
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        for i, c in enumerate(BAR_COLORS):
            d.rectangle([i * 8, 0, i * 8 + 7, 31], fill=c)
        for x in range(W):
            v = round(x * 255 / (W - 1))
            for y0, rgb in ((32, (v, v, v)), (40, (v, 0, 0)), (48, (0, v, 0)), (56, (0, 0, v))):
                d.rectangle([x, y0, x, y0 + 7], fill=rgb)
        return img

    def _grid(self, now):
        """Border, 8px grid, colored corners, 'TOP' label: orientation and mapping."""
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        for i in range(8, W, 8):
            d.line([(i, 0), (i, H - 1)], fill=(40, 40, 40))
            d.line([(0, i), (W - 1, i)], fill=(40, 40, 40))
        d.rectangle([0, 0, W - 1, H - 1], outline=(255, 255, 255))
        for (x, y), c in (((1, 1), (255, 0, 0)), ((W - 4, 1), (0, 255, 0)),
                          ((1, H - 4), (0, 0, 255)), ((W - 4, H - 4), (255, 255, 255))):
            d.rectangle([x, y, x + 2, y + 2], fill=c)
        d.line([(W // 2 - 3, H // 2), (W // 2 + 3, H // 2)], fill=(255, 255, 0))
        d.line([(W // 2, H // 2 - 3), (W // 2, H // 2 + 3)], fill=(255, 255, 0))
        font.draw_text(d, "TOP", (W - font.text_width("TOP")) // 2, 3, (255, 255, 255))
        return img

    def _scan(self, now):
        """A line sweeping down and one sweeping across: dead rows/columns, half-lit panel."""
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        y, x = int(now * 24) % H, int(now * 24) % W
        d.line([(0, y), (W - 1, y)], fill=(255, 255, 255))
        d.line([(x, 0), (x, H - 1)], fill=(0, 160, 255))
        return img

    def _fill(self, now):
        """Full-screen red, green, blue, white (about 1 s each). White = worst-case power draw."""
        return Image.new("RGB", (W, H), FILL_COLORS[int(now) % len(FILL_COLORS)])
