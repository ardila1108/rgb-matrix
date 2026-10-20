from datetime import datetime, timezone

import pytest

import settings
from ledwall import icons
from ledwall.screens import WeatherScreen
from ledwall.screens import weather as weather_module

DRY = [0] * 12


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


NOON = utc(2026, 10, 19, 11, 0)                 # 13:00 in Spain
FIRST_QUARTER = utc(2024, 10, 10, 20, 0)        # moon lit on the right
LAST_QUARTER = utc(2024, 10, 24, 8, 0)          # moon lit on the left


def data(**over):
    base = {"temp": 21, "code": 2, "is_day": True, "hi": 23, "lo": 14, "rain": DRY}
    base.update(over)
    return base


def screen(when=NOON, content=None, at=0.0):
    s = WeatherScreen(now=lambda: when)
    if content is not None:
        s.update(content, now=at)
    return s


def lit(img, box, color=None):
    x0, y0, x1, y1 = box
    return [(x, y) for x in range(x0, x1) for y in range(y0, y1)
            if (img.getpixel((x, y)) == color if color else img.getpixel((x, y)) != (0, 0, 0))]


def test_frame_is_64x64_rgb():
    img = screen(content=data()).render(0.0)
    assert img.size == (64, 64) and img.mode == "RGB"


def test_loading_message_before_data_but_the_sky_still_shows():
    img = screen().render(0.0)
    assert lit(img, (0, 10, 64, 18))                       # LOADING
    assert lit(img, (2, 48, 62, 52))                       # the sky strip needs no data


@pytest.mark.parametrize("code", [0, 1, 2, 3, 45, 48, 51, 55, 61, 65, 67, 71, 75, 80, 82, 85, 95, 96, 99, 1234])
@pytest.mark.parametrize("is_day", [True, False])
def test_every_weather_code_renders_day_and_night(code, is_day):
    img = screen(content=data(code=code, is_day=is_day)).render(0.0)
    assert lit(img, (2, 2, 27, 27))                        # an icon is drawn


def test_temperature_and_hi_lo_are_drawn():
    img = screen(content=data()).render(0.0)
    assert lit(img, (30, 3, 55, 17), (255, 255, 255))
    assert lit(img, (30, 19, 52, 24), (255, 150, 60))      # high
    assert lit(img, (30, 19, 52, 24), (110, 170, 255))     # low


def test_three_character_temperatures_stay_on_screen():
    img = screen(content=data(temp=-12, hi=-5, lo=-15)).render(0.0)
    assert all(img.getpixel((x, 3)) != (0, 0, 0) for x in (61, 62, 63))     # the degree ring fits


def test_rain_bars_follow_the_percentages():
    img = screen(content=data(rain=[100, 0, 50, 10] + [0] * 8)).render(0.0)
    assert img.getpixel((3, 30)) == (80, 180, 255)         # 100% = 14 px tall, bright
    assert img.getpixel((8, 43)) == (0, 0, 0)              # 0% = no bar
    assert img.getpixel((13, 40)) == (60, 130, 230)        # 50% bar
    assert img.getpixel((18, 43)) == (40, 80, 130)         # 10% = low and dim
    assert img.getpixel((18, 41)) == (0, 0, 0)


def test_rain_soon_pulses_a_blue_border():
    img_on = screen(content=data(rain=[70] + [0] * 11)).render(0.0)       # tick 0
    img_off = screen(content=data(rain=[70] + [0] * 11)).render(0.5)      # tick 1
    assert img_on.getpixel((0, 20)) == weather_module.ALERT_BLUE
    assert img_off.getpixel((0, 20)) == (0, 0, 0)


def test_no_border_below_the_threshold_or_beyond_the_alert_hours():
    below = screen(content=data(rain=[settings.RAIN_ALERT_PERCENT - 1] * 12)).render(0.0)
    later = screen(content=data(rain=[0] * settings.RAIN_ALERT_HOURS + [100] * 10)).render(0.0)
    assert below.getpixel((0, 20)) == (0, 0, 0) and later.getpixel((0, 20)) == (0, 0, 0)


def test_old_data_turns_the_temperature_gray():
    s = screen(content=data(), at=0.0)
    fresh = s.render(10.0)
    stale = s.render(settings.WEATHER_STALE_SECONDS + 10.0)
    assert lit(fresh, (30, 3, 55, 17), (255, 255, 255))
    assert not lit(stale, (30, 3, 55, 17), (255, 255, 255))
    assert lit(stale, (30, 3, 55, 17), (110, 110, 110))


def test_rain_animation_moves_between_frames():
    s = screen(content=data(code=63, rain=DRY))
    assert s.render(0.0).tobytes() != s.render(1.0).tobytes()


def moon_halves(img, box, cx):
    pixels = lit(img, box, icons.MOON_LIT)
    return sum(1 for x, _ in pixels if x > cx), sum(1 for x, _ in pixels if x < cx)


def test_small_moon_shows_todays_phase():
    # the model uses the mean lunar cycle (about a day off), so check which side dominates
    right, left = moon_halves(screen(FIRST_QUARTER, data()).render(0.0), (26, 53, 37, 63), 31)
    assert right > 0 and right > 3 * left                  # waxing: lit on the right
    right, left = moon_halves(screen(LAST_QUARTER, data()).render(0.0), (26, 53, 37, 63), 31)
    assert left > 0 and left > 3 * right                   # waning: lit on the left


def test_big_night_moon_shows_the_phase_too():
    night = data(code=0, is_day=False)
    right, left = moon_halves(screen(FIRST_QUARTER, night).render(0.0), (4, 4, 25, 25), 14)
    assert right > 20 and right > 3 * left
    right, left = moon_halves(screen(LAST_QUARTER, night).render(0.0), (4, 4, 25, 25), 14)
    assert left > 20 and left > 3 * right


def test_new_moon_is_dark_and_full_moon_is_round():
    night = data(code=0, is_day=False)
    new = lit(screen(utc(2024, 10, 2, 18, 49), night).render(0.0), (4, 4, 25, 25), icons.MOON_LIT)
    full = lit(screen(utc(2024, 10, 17, 11, 26), night).render(0.0), (4, 4, 25, 25), icons.MOON_LIT)
    assert len(new) < 15 and len(full) > 200


def test_sky_marker_is_a_sun_by_day_and_a_moon_at_night():
    day = screen(utc(2026, 10, 19, 11, 0), data()).render(0.0)                  # 13:00 local
    night = screen(utc(2026, 10, 19, 21, 30), data()).render(0.0)               # 23:30 local
    assert day.getpixel((2 + round(13 / 24 * 59), 49)) == (255, 230, 60)
    assert night.getpixel((2 + round(23.5 / 24 * 59), 49)) == (235, 235, 215)


def test_sunrise_and_sunset_times_are_written():
    img = screen(content=data()).render(0.0)
    assert lit(img, (6, 55, 24, 60), (255, 255, 255))      # sunrise time
    assert lit(img, (44, 55, 62, 60), (255, 255, 255))     # sunset time
