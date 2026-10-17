import pytest

import settings
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen


def snapshot():
    return [
        {"name": "CITY", "buses": [{"line": "24", "minutes": 12, "walk_min": 4}]},
        {"name": "AIRPORT", "buses": [{"line": "7", "minutes": 4, "walk_min": 4}]},
        {"name": "EMPTY", "buses": []},
    ]


def pixel(img, xy):
    return img.getpixel(xy)


def test_frame_is_64x64_rgb():
    s = BusScreen()
    s.update(snapshot(), now=0)
    img = s.render(0.0)
    assert img.size == (64, 64) and img.mode == "RGB"


def test_no_data_and_no_buses_messages_render():
    s = BusScreen()
    assert s.render(0.0).size == (64, 64)
    s.update([{"name": "A", "buses": []}], now=0)
    assert s.render(0.0).size == (64, 64)


def test_badge_and_urgency_color_on_first_row():
    s = BusScreen()
    s.update(snapshot(), now=0)
    img = s.render(0.0)
    assert pixel(img, (3, 16)) == settings.COLOR_BADGE            # badge fill
    colors = {img.getpixel((x, y)) for x in range(26, 48) for y in range(13, 27)}
    assert settings.COLOR_RELAX in colors                          # 12 min, 4 walk


def test_pages_advance_after_dwell_and_skip_empty():
    s = BusScreen()
    s.update(snapshot(), now=0)
    s.render(0.0)
    assert s._cur == "CITY"
    s.render(settings.DWELL_SECONDS + 0.01)                        # starts sliding
    s.render(settings.DWELL_SECONDS + settings.TRANSITION_SECONDS + 0.1)
    assert s._cur == "AIRPORT"
    s.render(2 * settings.DWELL_SECONDS + 1)
    s.render(2 * settings.DWELL_SECONDS + 2)
    assert s._cur == "CITY"                                        # wrapped, EMPTY skipped


def test_single_page_never_transitions():
    s = BusScreen()
    s.update([snapshot()[0]], now=0)
    s.render(0.0)
    s.render(100.0)
    assert s._cur == "CITY" and s._trans is None


def test_leave_now_dot_is_lit_purple_on_other_page():
    s = BusScreen()
    s.update(snapshot(), now=0)
    # dots: n=2, pitch 3, x0=58 -> second dot at x=61,y=3
    for t in (0.0, 0.5):                                           # steady in both blink phases
        img = s.render(t)
        assert pixel(img, (61, 3)) == settings.COLOR_LEAVE
        assert pixel(img, (58, 3)) == settings.COLOR_TEXT          # active page dot


def test_gone_bus_lights_dot_red_and_purple_wins_over_red(monkeypatch):
    s = BusScreen()
    s.update([
        {"name": "A", "buses": [{"line": "1", "minutes": 20, "walk_min": 3}]},
        {"name": "B", "buses": [{"line": "2", "minutes": 1, "walk_min": 3}]},
        {"name": "C", "buses": [{"line": "3", "minutes": 1, "walk_min": 3},
                                {"line": "4", "minutes": 4, "walk_min": 4}]},
    ], now=0)
    img = s.render(0.0)                      # n=3 -> x0=55; dots at 55, 58, 61
    assert pixel(img, (55, 3)) == settings.COLOR_TEXT              # active A
    assert pixel(img, (58, 3)) == settings.COLOR_GONE              # B: red only
    assert pixel(img, (61, 3)) == settings.COLOR_LEAVE             # C: purple beats red


def test_dot_blink_option(monkeypatch):
    monkeypatch.setattr(settings, "DOT_BLINK", True)
    s = BusScreen()
    s.update(snapshot(), now=0)
    assert pixel(s.render(0.0), (61, 3)) == settings.COLOR_LEAVE
    assert pixel(s.render(0.5), (61, 3)) == settings.COLOR_DOT_OFF


def test_stale_data_turns_progress_line_red():
    s = BusScreen()
    s.update(snapshot(), now=0)
    img = s.render(settings.STALE_AFTER_SECONDS + 1)
    assert pixel(img, (40, 10)) == settings.COLOR_STALE


def test_gone_bus_blinks():
    s = BusScreen()
    s.update([{"name": "A", "buses": [{"line": "1", "minutes": 1, "walk_min": 3}]}], now=0)
    on, off = s.render(0.0), s.render(0.5)
    def has_red(img):
        return any(img.getpixel((x, y)) == settings.COLOR_GONE
                   for x in range(26, 48) for y in range(13, 27))
    assert has_red(on) and not has_red(off)


def test_manager_switches_and_rejects_unknown():
    m = ScreenManager([BusScreen()])
    assert m.active == "bus"
    with pytest.raises(KeyError):
        m.set_active("weather")
