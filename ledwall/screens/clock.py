"""Clock screen: time and date in Spain (settings.TIMEZONE)."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

import settings
from .. import font
from .base import Screen

W, H = 64, 64
BLACK = (0, 0, 0)
TIME_COLOR = (255, 255, 255)
SECONDS_COLOR = (0, 200, 255)
SECONDS_TRACK = (28, 28, 28)
WEEKDAY_COLOR = (255, 190, 0)
DATE_COLOR = (255, 255, 255)
MONTH_COLOR = (0, 200, 255)
YEAR_COLOR = (110, 110, 110)

WEEKDAYS = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO"]
MONTHS = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]


def format_time(moment):
    """('14', '05') for a datetime."""
    return f"{moment.hour:02d}", f"{moment.minute:02d}"


def format_date(moment):
    """('LUNES', '19', 'OCT', '2026') for a datetime."""
    return (WEEKDAYS[moment.weekday()], str(moment.day), MONTHS[moment.month - 1], str(moment.year))


class ClockScreen(Screen):
    name = "clock"
    label = "Clock"
    icon = "🕒"
    fps = 4                     # the colon blinks once a second

    def __init__(self, now=None):
        # `now` returns an aware datetime (UTC is fine); injected in tests.
        self._now = now or (lambda: datetime.now(timezone.utc))

    def update(self, data=None):
        pass                                   # the clock needs no data

    def local_now(self):
        return self._now().astimezone(ZoneInfo(settings.TIMEZONE))

    def render(self, now):
        moment = self.local_now()
        hours, minutes = format_time(moment)
        weekday, day, month, year = format_date(moment)

        img = Image.new("RGB", (W, H), BLACK)
        d = ImageDraw.Draw(img)

        # HH:MM, 2x scaled; the colon blinks once per second
        x, y = 6, 4
        font.draw_text(d, hours, x, y, TIME_COLOR, sx=2, sy=2)
        if moment.second % 2 == 0:
            cx = x + 22 + 3
            d.rectangle([cx, y + 3, cx + 1, y + 4], fill=TIME_COLOR)
            d.rectangle([cx, y + 9, cx + 1, y + 10], fill=TIME_COLOR)
        font.draw_text(d, minutes, x + 22 + 3 + 2 + 3, y, TIME_COLOR, sx=2, sy=2)

        # seconds as a line under the time
        filled = round((moment.second + moment.microsecond / 1e6) / 60 * 52)
        for i in range(52):
            d.point((6 + i, 21), fill=SECONDS_COLOR if i < filled else SECONDS_TRACK)

        # weekday, centered
        font.draw_text(d, weekday, (W - font.text_width(weekday)) // 2, 27, WEEKDAY_COLOR)

        # day and month, 2x
        font.draw_text(d, day, 1, 39, DATE_COLOR, sx=2, sy=2)
        font.draw_text(d, month, 29, 39, MONTH_COLOR, sx=2, sy=2)

        # year, small and dim
        font.draw_text(d, year, (W - font.text_width(year)) // 2, 56, YEAR_COLOR)
        return img
