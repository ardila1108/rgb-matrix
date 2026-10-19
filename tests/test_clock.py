from datetime import datetime, timezone

import settings
from ledwall.screens import ClockScreen
from ledwall.screens.clock import format_date, format_time


def at(*args):
    return lambda: datetime(*args, tzinfo=timezone.utc)


def test_spain_summer_time_is_utc_plus_two():
    clock = ClockScreen(now=at(2026, 10, 19, 12, 5))       # October: CEST
    moment = clock.local_now()
    assert format_time(moment) == ("14", "05")


def test_spain_winter_time_is_utc_plus_one():
    clock = ClockScreen(now=at(2026, 12, 1, 12, 5))        # December: CET
    assert format_time(clock.local_now()) == ("13", "05")


def test_date_rolls_over_at_spanish_midnight():
    clock = ClockScreen(now=at(2026, 10, 19, 22, 30))      # 00:30 on the 20th in Spain
    moment = clock.local_now()
    assert format_time(moment) == ("00", "30")
    assert format_date(moment) == ("MARTES", "20", "OCT", "2026")


def test_spanish_names():
    assert format_date(datetime(2026, 10, 21)) == ("MIERCOLES", "21", "OCT", "2026")
    assert format_date(datetime(2026, 1, 3))[0] == "SABADO"
    assert format_date(datetime(2026, 12, 6)) == ("DOMINGO", "6", "DIC", "2026")


def test_timezone_is_a_setting(monkeypatch):
    monkeypatch.setattr(settings, "TIMEZONE", "UTC")
    clock = ClockScreen(now=at(2026, 10, 19, 12, 5))
    assert format_time(clock.local_now()) == ("12", "05")


def test_frame_is_64x64_and_draws_time_and_date():
    img = ClockScreen(now=at(2026, 10, 19, 12, 5)).render(0.0)
    assert img.size == (64, 64) and img.mode == "RGB"
    lit = lambda box: any(img.getpixel((x, y)) != (0, 0, 0)
                          for x in range(box[0], box[2]) for y in range(box[1], box[3]))
    assert lit((6, 4, 58, 18))        # time
    assert lit((0, 27, 64, 34))       # weekday
    assert lit((1, 39, 63, 53))       # day + month
    assert lit((0, 56, 64, 63))       # year


def test_colon_blinks_every_second():
    colon = lambda s: ClockScreen(now=lambda: datetime(2026, 10, 19, 12, 5, s, tzinfo=timezone.utc)
                                  ).render(0.0).getpixel((31, 7))
    assert colon(0) != colon(1)
