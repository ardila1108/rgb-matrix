import pytest
from PIL import Image

import settings
from ledwall.frames import FrameGate
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen, ClockScreen, FreestyleScreen, TestScreen, WeatherScreen


def img(color):
    return Image.new("RGB", (64, 64), color)


def test_first_frame_is_always_sent():
    assert FrameGate().changed(img((0, 0, 0)), 80)


def test_identical_frames_are_not_sent_again():
    gate = FrameGate()
    gate.changed(img((255, 0, 0)), 80)
    assert not gate.changed(img((255, 0, 0)), 80)
    assert not gate.changed(img((255, 0, 0)), 80)


def test_a_different_frame_is_sent_and_becomes_the_reference():
    gate = FrameGate()
    gate.changed(img((255, 0, 0)), 80)
    assert gate.changed(img((0, 255, 0)), 80)
    assert not gate.changed(img((0, 255, 0)), 80)
    assert gate.changed(img((255, 0, 0)), 80)


def test_a_brightness_change_forces_a_resend_because_the_panel_applies_it_when_pixels_are_written():
    gate = FrameGate()
    gate.changed(img((255, 255, 255)), 80)
    assert gate.changed(img((255, 255, 255)), 40)
    assert not gate.changed(img((255, 255, 255)), 40)


def test_one_pixel_is_enough_to_count_as_a_change():
    gate = FrameGate()
    a = img((0, 0, 0))
    gate.changed(a, 80)
    b = a.copy()
    b.putpixel((63, 63), (1, 0, 0))
    assert gate.changed(b, 80)


# -- how often each screen is redrawn -------------------------------------------------------
def test_static_looking_screens_are_redrawn_slowly():
    assert ClockScreen.fps == 4 and WeatherScreen.fps == 4
    assert FreestyleScreen().fps == 10 and TestScreen().fps == 10


def test_bus_screen_is_smooth_only_while_sliding():
    bus = BusScreen()
    bus.update([{"name": "A", "buses": [{"line": "1", "minutes": 9, "walk_min": 3}]},
                {"name": "B", "buses": [{"line": "2", "minutes": 9, "walk_min": 3}]}], now=0)
    bus.render(0.0)
    assert bus.fps == 8
    bus.render(settings.DWELL_SECONDS + 0.01)                 # a slide begins
    assert bus.fps == settings.FPS
    bus.render(settings.DWELL_SECONDS + settings.TRANSITION_SECONDS + 0.2)
    assert bus.fps == 8


def test_manager_uses_the_active_screens_rate_and_falls_back_to_the_default():
    class Plain(ClockScreen):
        name, fps = "plain", None

    manager = ScreenManager([ClockScreen(), Plain()], active="clock")
    assert manager.fps == 4
    manager.set_active("plain")
    assert manager.fps == settings.FPS


def test_a_still_clock_second_produces_one_new_frame_not_many():
    from datetime import datetime, timezone
    clock = ClockScreen(now=lambda: datetime(2026, 10, 19, 12, 5, 7, 100000, tzinfo=timezone.utc))
    gate = FrameGate()
    sent = sum(gate.changed(clock.render(0.0), 80) for _ in range(20))
    assert sent == 1
