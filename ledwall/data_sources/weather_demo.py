"""Fake weather that cycles through every look, so you can see them all."""
import time

SECONDS_PER_SCENE = 8

_RAIN_DRY = [0, 0, 5, 5, 10, 5, 0, 0, 0, 5, 0, 0]
_RAIN_SOON = [60, 85, 90, 70, 55, 40, 30, 20, 15, 10, 10, 5]
_RAIN_SOME = [5, 10, 20, 35, 45, 30, 20, 10, 5, 5, 0, 0]

SCENES = [
    {"temp": 21, "code": 2, "is_day": True, "hi": 23, "lo": 14, "rain": _RAIN_SOME},     # partly cloudy
    {"temp": 26, "code": 0, "is_day": True, "hi": 28, "lo": 17, "rain": _RAIN_DRY},      # clear
    {"temp": 14, "code": 63, "is_day": True, "hi": 16, "lo": 11, "rain": _RAIN_SOON},    # rain soon
    {"temp": 11, "code": 3, "is_day": True, "hi": 13, "lo": 8, "rain": _RAIN_SOME},      # overcast
    {"temp": 9, "code": 45, "is_day": True, "hi": 12, "lo": 7, "rain": _RAIN_DRY},       # fog
    {"temp": -3, "code": 73, "is_day": True, "hi": 0, "lo": -6, "rain": _RAIN_SOME},     # snow, negative
    {"temp": 17, "code": 95, "is_day": True, "hi": 19, "lo": 14, "rain": _RAIN_SOON},    # storm
    {"temp": 12, "code": 0, "is_day": False, "hi": 17, "lo": 9, "rain": _RAIN_DRY},      # clear night: moon
    {"temp": 13, "code": 2, "is_day": False, "hi": 17, "lo": 9, "rain": _RAIN_DRY},      # partly cloudy night
]


def fetch_weather():
    return dict(SCENES[int(time.time() / SECONDS_PER_SCENE) % len(SCENES)])
