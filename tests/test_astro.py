from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from ledwall import astro

MADRID = ZoneInfo("Europe/Madrid")
DONOSTIA = (43.3183, -1.9812)


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def circular_gap(a, b):
    gap = abs(a - b) % 1.0
    return min(gap, 1 - gap)


@pytest.mark.parametrize("moment,expected", [
    (utc(2024, 10, 2, 18, 49), 0.0),       # new moon (annular eclipse)
    (utc(2024, 10, 10, 18, 55), 0.25),     # first quarter
    (utc(2024, 10, 17, 11, 26), 0.5),      # full moon (Hunter's Moon)
    (utc(2024, 10, 24, 8, 3), 0.75),       # last quarter
])
def test_moon_phase_matches_known_events_within_a_day(moment, expected):
    assert circular_gap(astro.moon_phase(moment), expected) < 0.04     # about 1.2 days


def test_phase_is_always_between_0_and_1():
    for year in (1999, 2026, 2060):
        for month in range(1, 13):
            assert 0 <= astro.moon_phase(utc(year, month, 15, 12)) < 1


def test_illumination_and_names():
    assert astro.moon_illumination(0.0) == pytest.approx(0)
    assert astro.moon_illumination(0.25) == pytest.approx(0.5)
    assert astro.moon_illumination(0.5) == pytest.approx(1)
    assert astro.moon_name(0.0) == "New moon" and astro.moon_name(0.99) == "New moon"
    assert astro.moon_name(0.25) == "First quarter" and astro.moon_name(0.5) == "Full moon"
    assert astro.moon_name(0.75) == "Last quarter"


def minutes_between(moment, hour, minute):
    return abs((moment.hour * 60 + moment.minute) - (hour * 60 + minute))


def test_sun_times_donostia_match_an_independent_calculation():
    rise, sunset = astro.sun_times(date(2026, 10, 19), *DONOSTIA, MADRID)
    assert minutes_between(rise, 8, 26) <= 3 and minutes_between(sunset, 19, 18) <= 3
    rise, sunset = astro.sun_times(date(2026, 6, 21), *DONOSTIA, MADRID)
    assert minutes_between(rise, 6, 27) <= 3 and minutes_between(sunset, 21, 51) <= 3


def test_times_follow_daylight_saving():
    before = astro.sun_times(date(2026, 10, 24), *DONOSTIA, MADRID)[0]
    after = astro.sun_times(date(2026, 10, 26), *DONOSTIA, MADRID)[0]
    assert before.utcoffset().total_seconds() == 2 * 3600
    assert after.utcoffset().total_seconds() == 1 * 3600


def test_days_are_longer_in_summer_and_in_the_right_hemisphere():
    def length(day, lat, lon, tz):
        rise, sunset = astro.sun_times(day, lat, lon, tz)
        return (sunset - rise).total_seconds() / 3600
    assert length(date(2026, 6, 21), *DONOSTIA, MADRID) > 15
    assert length(date(2026, 12, 21), *DONOSTIA, MADRID) < 9.5
    assert length(date(2026, 12, 21), -33.87, 151.21, ZoneInfo("Australia/Sydney")) > 14


def test_polar_night_has_no_sunrise():
    assert astro.sun_times(date(2026, 12, 21), 78.2, 15.6, ZoneInfo("UTC")) is None
