"""Weather screen: weather now, rain chances for 12 hours, sun and moon."""
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

import settings
from .. import astro, font, icons
from ..data_sources.weather import classify_weather
from .base import Screen

W, H = 64, 64
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (110, 110, 110)
HI_COLOR = (255, 150, 60)
LO_COLOR = (110, 170, 255)
NIGHT_SKY = (10, 12, 45)
DAWN_SKY = (255, 120, 40)
GOLDEN_SKY = (255, 185, 90)
DAY_SKY = (60, 150, 255)
SUNRISE_ARROW = (255, 150, 60)
SUNSET_ARROW = (255, 100, 40)
ALERT_BLUE = (30, 90, 200)
STARS_CLEAR = [(3, 4), (24, 5), (22, 23), (4, 22), (27, 13), (8, 2)]
STARS_PARTLY = [(20, 4), (3, 17), (24, 9)]


def _hours(moment):
    return moment.hour + moment.minute / 60


class WeatherScreen(Screen):
    name = "weather"
    label = "Weather"
    icon = "🌤️"
    fps = 4                     # animations tick twice a second

    def __init__(self, now=None):
        # `now` returns an aware datetime (UTC is fine); injected in tests.
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._data = None
        self._received = None

    def update(self, data, now=None):
        """data: {"temp", "code", "is_day", "hi", "lo", "rain": [12 percentages]}"""
        with self._lock:
            self._data = data
            self._received = time.monotonic() if now is None else now

    def render(self, mono):
        moment = self._now().astimezone(ZoneInfo(settings.TIMEZONE))
        phase = astro.moon_phase(moment)
        tick = int(mono * 2)
        with self._lock:
            data, received = self._data, self._received

        img = Image.new("RGB", (W, H), BLACK)
        d = ImageDraw.Draw(img)

        if data is None:
            text = "LOADING"
            font.draw_text(d, text, (W - font.text_width(text)) // 2, 10, GRAY)
        else:
            stale = (mono - received) > settings.WEATHER_STALE_SECONDS
            self._hero(d, data, phase, tick)
            self._temperature(d, data, stale)
            self._rain_bars(d, data["rain"])
            soon = data["rain"][:settings.RAIN_ALERT_HOURS]
            if soon and max(soon) >= settings.RAIN_ALERT_PERCENT and tick % 2 == 0:
                d.rectangle([0, 0, W - 1, H - 1], outline=ALERT_BLUE)

        self._sky(d, moment, phase)
        return img

    # -- top: icon and temperature ---------------------------------------------------
    def _hero(self, d, data, phase, tick):
        kind = classify_weather(data["code"], data["is_day"])
        day = data["is_day"]
        if kind == "clear":
            if day:
                icons.sun(d, 14, 14, 7, tick)
            else:
                icons.moon(d, 14, 14, 9, phase)             # the real phase of the moon
                icons.stars(d, tick, STARS_CLEAR)
        elif kind == "partly":
            if day:
                icons.sun(d, 9, 9, 5, tick)
            else:
                icons.moon(d, 9, 9, 5, phase)
                icons.stars(d, tick, STARS_PARTLY)
            icons.cloud(d, 15, 16, icons.CLOUD_LIGHT)
        elif kind == "cloudy":
            icons.cloud(d, 14, 13, icons.CLOUD_GRAY)
        elif kind == "fog":
            icons.cloud(d, 14, 8, icons.CLOUD_GRAY)
            icons.fog(d, 14, 8)
        elif kind == "rain":
            icons.cloud(d, 14, 8, icons.CLOUD_DARK)
            icons.rain(d, 14, 8, tick)
        elif kind == "snow":
            icons.cloud(d, 14, 8, icons.CLOUD_GRAY)
            icons.snow(d, 14, 8, tick)
        elif kind == "storm":
            icons.cloud(d, 14, 8, icons.CLOUD_STORM)
            if tick % 3 != 0:
                icons.bolt(d, 14, 17)

    def _temperature(self, d, data, stale):
        text = str(data["temp"])
        spacing = 1 if len(text) <= 2 else 0               # keep three characters on screen
        end = font.draw_text(d, text, 30, 3, GRAY if stale else WHITE, sx=2, sy=2, spacing=spacing)
        font.draw_bitmap(d, ["111", "101", "111"], end - 2 * spacing + 1, 3, GRAY if stale else WHITE)
        x = font.draw_small(d, str(data["hi"]), 30, 19, HI_COLOR)
        x = font.draw_small(d, "/", x, 19, GRAY)
        font.draw_small(d, str(data["lo"]), x, 19, LO_COLOR)

    # -- middle: rain chance for the next 12 hours -----------------------------------
    def _rain_bars(self, d, rain):
        for i, percent in enumerate(rain[:12]):
            height = max(1, round(percent / 100 * 14)) if percent > 0 else 0
            if percent >= 60:
                color = (80, 180, 255)
            elif percent >= 30:
                color = (60, 130, 230)
            else:
                color = (40, 80, 130)
            x0 = 2 + i * 5
            if height:
                d.rectangle([x0, 44 - height, x0 + 3, 43], fill=color)
        d.line([(2, 44), (61, 44)], fill=(30, 30, 30))
        for i in range(0, 12, 3):
            d.point((3 + i * 5, 45), fill=(90, 90, 90))

    # -- bottom: the day as a strip, sunrise, moon phase, sunset ----------------------
    def _sky(self, d, moment, phase):
        times = astro.sun_times(moment.date(), settings.LATITUDE, settings.LONGITUDE, moment.tzinfo)
        rise = _hours(times[0]) if times else None
        sunset = _hours(times[1]) if times else None

        for x in range(2, 62):
            d.line([(x, 48), (x, 51)], fill=self._band((x - 2) / 60 * 24, rise, sunset))

        now_x = 2 + round(_hours(moment) / 24 * 59)
        daytime = times is not None and rise < _hours(moment) < sunset
        d.rectangle([now_x - 1, 47, now_x + 1, 52], fill=(255, 230, 60) if daytime else (235, 235, 215))

        rise_text = times[0].strftime("%H:%M") if times else "--:--"
        set_text = times[1].strftime("%H:%M") if times else "--:--"
        font.draw_bitmap(d, ["010", "111"], 2, 57, SUNRISE_ARROW)
        font.draw_small(d, rise_text, 6, 55, WHITE)
        icons.moon(d, 31, 58, 4, phase)                    # today's phase, small
        font.draw_bitmap(d, ["111", "010"], 40, 57, SUNSET_ARROW)
        font.draw_small(d, set_text, 44, 55, WHITE)

    @staticmethod
    def _band(hour, rise, sunset):
        if rise is None or hour < rise - 0.5 or hour > sunset + 0.5:
            return NIGHT_SKY
        if abs(hour - rise) <= 0.5 or abs(hour - sunset) <= 0.5:
            return DAWN_SKY
        if hour < rise + 1.5 or hour > sunset - 1.5:
            return GOLDEN_SKY
        return DAY_SKY
