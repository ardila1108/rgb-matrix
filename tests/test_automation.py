from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import settings
from ledwall.automation import Automation, Window, build_schedule, parse_hhmm
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen, ClockScreen, FreestyleScreen, TestScreen, WeatherScreen

MADRID = ZoneInfo("Europe/Madrid")
KNOWN = ["bus", "clock", "weather", "freestyle", "test"]


def at(hour, minute=0, day=19):
    """A moment in Madrid. 2026-10-19 is a Monday."""
    return datetime(2026, 10, day, hour, minute, tzinfo=MADRID)


def names(plan):
    return [n for n, _ in plan]


# ---- times and windows ----------------------------------------------------------------
@pytest.mark.parametrize("text,minutes", [("08:00", 480), ("8:05", 485), ("00:00", 0), ("23:59", 1439)])
def test_parse_hhmm(text, minutes):
    assert parse_hhmm(text) == minutes


@pytest.mark.parametrize("text", ["24:00", "8", "08:60", "eight", "", None, "08:00:00"])
def test_parse_hhmm_rejects_nonsense(text):
    with pytest.raises(ValueError):
        parse_hhmm(text)


def test_window_includes_start_and_excludes_end():
    w = Window(480, 660)
    assert w.active(at(8, 0)) and w.active(at(10, 59))
    assert not w.active(at(7, 59)) and not w.active(at(11, 0))


def test_window_crossing_midnight():
    w = Window(23 * 60, 7 * 60)
    for hour, minute in [(23, 0), (23, 59), (0, 0), (3, 30), (6, 59)]:
        assert w.active(at(hour, minute)), (hour, minute)
    for hour, minute in [(7, 0), (12, 0), (22, 59)]:
        assert not w.active(at(hour, minute)), (hour, minute)


def test_days_apply_to_the_day_a_window_starts():
    friday_night = Window(23 * 60, 7 * 60, days=frozenset({4}))        # Friday only
    assert friday_night.active(at(23, 30, day=23))                       # Friday evening
    assert friday_night.active(at(2, 0, day=24))                         # Saturday small hours
    assert not friday_night.active(at(23, 30, day=24))                   # Saturday evening
    assert not friday_night.active(at(2, 0, day=23))                     # Friday small hours (Thursday's)
    weekdays = Window(480, 660, days=frozenset({0, 1, 2, 3, 4}))
    assert weekdays.active(at(9, 0, day=19)) and not weekdays.active(at(9, 0, day=24))   # Mon yes, Sat no


# ---- the schedule from settings -----------------------------------------------------------
def test_your_example_day():
    sched = build_schedule(KNOWN)
    plan = lambda h, m=0: names(sched.plan_at(at(h, m)))
    assert plan(7, 59) == ["clock", "weather"]
    assert plan(8, 0) == ["bus"] and plan(10, 59) == ["bus"]
    assert plan(11, 0) == ["clock", "weather"] and plan(15, 59) == ["clock", "weather"]
    assert plan(16, 0) == ["bus"] and plan(18, 59) == ["bus"]
    assert plan(19, 0) == ["clock", "weather"] and plan(23, 30) == ["clock", "weather"]
    assert [s for _, s in sched.plan_at(at(12))] == [20.0, 20.0]


def test_your_example_brightness():
    sched = build_schedule(KNOWN)
    assert sched.brightness_at(at(22, 59)) == settings.BRIGHTNESS
    for hour, minute in [(23, 0), (0, 0), (3, 0), (6, 59)]:
        assert sched.brightness_at(at(hour, minute)) == 10
    assert sched.brightness_at(at(7, 0)) == settings.BRIGHTNESS


def cfg(**over):
    base = dict(ROTATION_SECONDS=20, DEFAULT_SCREENS=("clock", "weather"), SCREEN_SCHEDULE=[],
                BRIGHTNESS_SCHEDULE=[], BRIGHTNESS=80)
    base.update(over)
    return SimpleNamespace(**base)


def test_first_matching_window_wins():
    c = cfg(SCREEN_SCHEDULE=[{"from": "08:00", "to": "12:00", "screens": ("bus",)},
                             {"from": "10:00", "to": "14:00", "screens": ("clock",)}])
    sched = build_schedule(KNOWN, c)
    assert names(sched.plan_at(at(11))) == ["bus"] and names(sched.plan_at(at(13))) == ["clock"]


def test_rotation_seconds_can_be_set_per_window_and_per_screen():
    c = cfg(ROTATION_SECONDS=20, SCREEN_SCHEDULE=[
        {"from": "08:00", "to": "09:00", "screens": ("clock", "weather"), "seconds": 5},
        {"from": "09:00", "to": "10:00", "screens": ("clock", ("weather", 45))}])
    sched = build_schedule(KNOWN, c)
    assert sched.plan_at(at(8, 30)) == (("clock", 5.0), ("weather", 5.0))
    assert sched.plan_at(at(9, 30)) == (("clock", 20.0), ("weather", 45.0))


def test_days_in_the_schedule():
    c = cfg(SCREEN_SCHEDULE=[{"from": "08:00", "to": "11:00", "screens": ("bus",),
                              "days": ("mon", "Tuesday", "wed", "thu", "fri")}])
    sched = build_schedule(KNOWN, c)
    assert names(sched.plan_at(at(9, 0, day=19))) == ["bus"]              # Monday
    assert names(sched.plan_at(at(9, 0, day=24))) == ["clock", "weather"] # Saturday


def test_every_mistake_is_reported_at_once():
    c = cfg(DEFAULT_SCREENS=("clock", "radio"), ROTATION_SECONDS=20,
            SCREEN_SCHEDULE=[{"from": "8am", "to": "11:00", "screens": ("bus",)},
                             {"from": "08:00", "to": "08:00", "screens": ("bus",)},
                             {"from": "08:00", "to": "09:00", "screens": ()},
                             {"from": "08:00", "to": "09:00", "screens": ("bus",), "days": ("funday",)},
                             {"from": "08:00", "to": "09:00", "screens": (("clock", -3),)}],
            BRIGHTNESS_SCHEDULE=[{"from": "23:00", "to": "07:00", "brightness": 0},
                                 {"from": "23:00", "to": "07:00", "brightness": 150},
                                 {"from": "23:00", "to": "07:00"}])
    with pytest.raises(ValueError) as error:
        build_schedule(KNOWN, c)
    text = str(error.value)
    for expected in ["'8am'", "same time", "at least one screen", "unknown day", "bad screen entry",
                     "whole number from 1 to 100", "unknown screen 'radio'"]:
        assert expected in text, expected


def test_the_shipped_settings_are_valid():
    build_schedule(KNOWN)


# ---- the controller -------------------------------------------------------------------------
class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


class Display:
    def __init__(self):
        self.brightness, self.calls = settings.BRIGHTNESS, []

    def set_brightness(self, percent):
        self.brightness = percent
        self.calls.append(percent)


class Rig:
    def __init__(self, hour, minute=0, enabled=True):
        self.when = at(hour, minute)
        self.clock = Clock()
        self.manager = ScreenManager([BusScreen(), ClockScreen(), WeatherScreen(), FreestyleScreen(), TestScreen()],
                                     active="freestyle")
        self.display = Display()
        self.auto = Automation(build_schedule(KNOWN), self.manager, display=self.display,
                               enabled=enabled, now=lambda: self.when, clock=self.clock)

    def tick(self, advance=1.0, when=None):
        self.clock.advance(advance)
        if when is not None:
            self.when = when
        self.auto.tick()
        return self.manager.active


def test_rotation_alternates_every_20_seconds():
    rig = Rig(12)
    assert rig.tick() == "clock"               # the rotation starts here (0 s)
    assert rig.tick(18) == "clock"             # 18 s in
    assert rig.tick(2.5) == "weather"          # 20.5 s in
    assert rig.tick(18) == "weather"           # 38.5 s in
    assert rig.tick(3) == "clock"              # 41.5 s in
    assert rig.tick(20) == "weather"           # 61.5 s in


def test_bus_window_pins_the_bus_and_rotation_restarts_afterwards():
    rig = Rig(7, 59)
    assert rig.tick() == "clock"
    assert rig.tick(30, at(8, 0)) == "bus"                     # window starts: bus right away
    assert rig.tick(5000, at(10, 59)) == "bus"
    assert rig.tick(1, at(11, 0)) == "clock"                   # rotation starts again with the clock
    assert rig.tick(21) == "weather"
    assert rig.tick(60, at(16, 0)) == "bus"
    assert rig.tick(60, at(19, 0)) == "clock"


def test_a_manual_choice_holds_for_the_configured_time_then_the_schedule_returns():
    rig = Rig(9)                                               # bus window
    assert rig.tick() == "bus"
    rig.manager.set_active("clock")
    rig.auto.hold()
    assert rig.tick(10 * 60) == "clock"
    assert rig.tick(19 * 60) == "clock"                        # 29 minutes in
    assert rig.tick(2 * 60) == "bus"                           # past 30 minutes


def test_hold_length_is_a_setting_and_zero_means_until_resumed(monkeypatch):
    monkeypatch.setattr(settings, "MANUAL_HOLD_MINUTES", 0)
    rig = Rig(9)
    rig.tick()
    rig.manager.set_active("weather")
    rig.auto.hold()
    assert rig.tick(24 * 3600) == "weather"                    # forever
    rig.auto.set_enabled(True)                                 # "resume"
    assert rig.tick() == "bus"


def test_disabled_automation_changes_nothing_and_ignores_holds():
    rig = Rig(9, enabled=False)
    assert rig.tick() == "freestyle" and rig.display.calls == []
    rig.auto.hold()
    assert rig.auto.status()["holding"] is False


def test_enabling_applies_the_schedule_immediately():
    rig = Rig(2, enabled=False)
    rig.tick()
    assert rig.display.calls == []
    rig.auto.set_enabled(True)
    assert rig.tick() == "clock" and rig.display.calls == [10]


def test_night_brightness_is_applied_at_startup_and_only_at_transitions():
    rig = Rig(2)                                               # started in the middle of the night
    rig.tick()
    assert rig.display.calls == [10]
    rig.tick(60)
    assert rig.display.calls == [10]                           # not repeated
    rig.display.set_brightness(50)                             # you move the slider
    rig.display.calls.clear()
    rig.tick(3600, at(3, 0))
    rig.tick(3600, at(6, 30))
    assert rig.display.brightness == 50 and rig.display.calls == []   # your choice sticks
    rig.tick(3600, at(7, 0))
    assert rig.display.calls == [settings.BRIGHTNESS]          # next scheduled change wins
    rig.tick(3600, at(23, 0))
    assert rig.display.calls == [settings.BRIGHTNESS, 10]


def test_brightness_follows_the_schedule_even_while_a_screen_is_held():
    rig = Rig(22, 59)
    rig.tick()
    rig.auto.hold()
    rig.manager.set_active("clock")
    rig.tick(60, at(23, 0))
    assert rig.display.brightness == 10 and rig.manager.active == "clock"


def test_ticks_closer_than_a_fifth_of_a_second_are_skipped():
    rig = Rig(12)
    rig.tick()
    rig.when = at(9, 0)
    rig.clock.advance(0.05)
    rig.auto.tick()
    assert rig.manager.active == "clock"                       # not re-evaluated yet
    rig.clock.advance(0.3)
    rig.auto.tick()
    assert rig.manager.active == "bus"


def test_status_describes_what_is_going_on():
    rig = Rig(9)
    rig.tick()
    st = rig.auto.status()
    assert st["enabled"] and st["plan"] == ["bus"] and not st["rotating"] and st["until"] == "11:00"
    rig.when = at(12)
    st = rig.auto.status()
    assert st["plan"] == ["clock", "weather"] and st["rotating"] and st["seconds"] == 20 and st["until"] == "16:00"
    rig.when = at(20)
    assert rig.auto.status()["until"] == "Tue 08:00"           # next change is tomorrow
    rig.auto.hold()
    st = rig.auto.status()
    assert st["holding"] and st["hold_minutes"] == 30 and st["until"] is None
    rig.clock.advance(10 * 60)
    assert rig.auto.status()["hold_minutes"] == 20


def test_status_when_there_is_nothing_to_change():
    sched = build_schedule(KNOWN, cfg())
    auto = Automation(sched, ScreenManager([ClockScreen(), WeatherScreen()]), now=lambda: at(12), clock=Clock())
    assert auto.status()["until"] is None
