import json

import pytest

import settings
from ledwall.automation import Automation, build_schedule
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen, ClockScreen, FreestyleScreen, HalloweenScreen, TestScreen, WeatherScreen
from tests.test_automation import KNOWN, Clock, Display, Rig, at


def test_pinning_shows_the_screen_now_and_the_schedule_stops_moving_it():
    rig = Rig(9)                                               # bus window
    rig.tick()
    rig.auto.pin("weather")
    assert rig.manager.active == "weather"
    assert rig.tick(1) == "weather"
    assert rig.tick(3 * 3600, at(12)) == "weather"             # no rotation
    assert rig.tick(60, at(16, 30)) == "weather"               # no bus window either
    assert rig.tick(60, at(2, 0, day=20)) == "weather"         # and it stays all night


def test_unpinning_returns_to_the_schedule_immediately():
    rig = Rig(9)
    rig.tick()
    rig.auto.pin("weather")
    rig.tick(10)
    rig.auto.unpin()
    assert rig.auto.pinned is None
    assert rig.tick() == "bus"                                  # bus window


def test_pinning_another_screen_moves_the_pin():
    rig = Rig(12)
    rig.auto.pin("clock")
    rig.auto.pin("bus")
    assert rig.auto.pinned == "bus" and rig.manager.active == "bus"


def test_a_manual_peek_returns_to_the_pinned_screen_not_to_the_schedule():
    rig = Rig(9)                                               # the bus window would show the bus
    rig.tick()
    rig.auto.pin("clock")
    rig.manager.set_active("weather")                          # you tap Weather
    rig.auto.hold()
    assert rig.tick(10 * 60) == "weather"
    assert rig.tick(25 * 60) == "clock"                        # hold over: back to the pin


def test_the_pin_does_not_stop_the_brightness_schedule():
    rig = Rig(22, 59)
    rig.tick()
    rig.auto.pin("clock")
    rig.tick(60, at(23, 0))
    assert rig.display.brightness == 10 and rig.manager.active == "clock"


def test_pinning_works_while_automation_is_off_and_applies_when_it_comes_back():
    rig = Rig(9, enabled=False)
    rig.auto.pin("clock")
    assert rig.manager.active == "clock"                       # shown right away
    rig.manager.set_active("weather")
    rig.tick(5)
    assert rig.manager.active == "weather"                     # off: nothing moves it
    rig.auto.set_enabled(True)
    assert rig.tick() == "clock"                               # the pin is honored again


def test_unknown_screen_cannot_be_pinned():
    rig = Rig(12)
    with pytest.raises(KeyError):
        rig.auto.pin("radio")
    assert rig.auto.pinned is None


def test_status_reports_the_pin():
    rig = Rig(9)
    rig.tick()
    assert rig.auto.status()["pinned"] is None
    rig.auto.pin("clock")
    st = rig.auto.status()
    assert st["pinned"] == "clock" and st["plan"] == ["clock"] and not st["rotating"] and st["until"] is None
    rig.auto.unpin()
    assert rig.auto.status()["pinned"] is None


# ---- the pin survives restarts -----------------------------------------------------------
def make(path, when=None):
    manager = ScreenManager([BusScreen(), ClockScreen(), WeatherScreen(), HalloweenScreen(), FreestyleScreen(), TestScreen()])
    clock = Clock()
    auto = Automation(build_schedule(KNOWN), manager, display=Display(), now=lambda: when or at(9),
                      clock=clock, state_path=str(path))
    return auto, manager, clock


def test_pin_is_saved_and_loaded_after_a_restart(tmp_path):
    path = tmp_path / "data" / "state.json"
    first, _, _ = make(path)
    first.pin("weather")
    assert json.loads(path.read_text()) == {"pinned": "weather"}
    second, manager, clock = make(path)
    assert second.pinned == "weather"
    clock.advance(1)
    second.tick()
    assert manager.active == "weather"                         # even inside the bus window


def test_unpinning_is_saved_too(tmp_path):
    path = tmp_path / "state.json"
    auto, _, _ = make(path)
    auto.pin("clock")
    auto.unpin()
    assert json.loads(path.read_text()) == {"pinned": None}
    assert make(path)[0].pinned is None


@pytest.mark.parametrize("content", ["not json", '{"pinned": "radio"}', '{"pinned": 5}', "[]", ""])
def test_a_broken_or_stale_state_file_is_ignored(tmp_path, content):
    path = tmp_path / "state.json"
    path.write_text(content)
    assert make(path)[0].pinned is None


def test_no_state_path_means_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rig = Rig(12)
    rig.auto.pin("clock")
    assert list(tmp_path.iterdir()) == []
