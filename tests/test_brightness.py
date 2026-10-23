import io
import json
import sys
import types
import urllib.error
import urllib.request

import pytest
from PIL import Image

import settings
from ledwall.backends import HardwareBackend, SimulatorBackend
from ledwall.control import ControlServer
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen, ClockScreen


class FakeDisplay:
    def __init__(self):
        self.brightness = 50

    def set_brightness(self, percent):
        self.brightness = percent


def call(srv, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{srv.port}{path}", data=data,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


@pytest.fixture
def with_display():
    display = FakeDisplay()
    srv = ControlServer(ScreenManager([BusScreen(), ClockScreen()]), ("bus", "clock"),
                        port=0, host="127.0.0.1", display=display)
    srv.start()
    yield srv, display
    srv.stop()


def test_state_reports_brightness(with_display):
    srv, _ = with_display
    assert call(srv, "/api/state")[1]["brightness"] == 50


def test_setting_brightness_reaches_the_display(with_display):
    srv, display = with_display
    status, state = call(srv, "/api/brightness", {"value": 30})
    assert status == 200 and state["brightness"] == 30 and display.brightness == 30
    assert call(srv, "/api/brightness", {"value": 1})[0] == 200
    assert call(srv, "/api/brightness", {"value": 100})[0] == 200


@pytest.mark.parametrize("value", [0, 101, -5, 30.5, "30", None, True, [30]])
def test_bad_values_are_refused_and_change_nothing(with_display, value):
    srv, display = with_display
    assert call(srv, "/api/brightness", {"value": value})[0] == 400
    assert display.brightness == 50


def test_missing_value_is_refused(with_display):
    srv, _ = with_display
    assert call(srv, "/api/brightness", {})[0] == 400


def test_without_a_display_there_is_no_brightness_control():
    srv = ControlServer(ScreenManager([BusScreen()]), ("bus",), port=0, host="127.0.0.1")
    srv.start()
    try:
        assert "brightness" not in call(srv, "/api/state")[1]
        assert call(srv, "/api/brightness", {"value": 30})[0] == 404
    finally:
        srv.stop()


# -- simulator -------------------------------------------------------------------
def test_simulator_preview_dims_with_brightness():
    sim = SimulatorBackend(port=0)
    try:
        white = Image.new("RGB", (64, 64), (255, 255, 255))
        sim.set_brightness(100)
        sim.show(white)
        bright = Image.open(io.BytesIO(sim._png)).getpixel((4, 4))
        sim.set_brightness(25)
        sim.show(white)
        dim = Image.open(io.BytesIO(sim._png)).getpixel((4, 4))
        assert bright[0] > 240 and 55 <= dim[0] <= 75
        sim.set_brightness(500)
        assert sim.brightness == 100                       # clamped
        sim.set_brightness(0)
        assert sim.brightness == 1
    finally:
        sim.close()


# -- hardware (with a stand-in for the panel library) ---------------------------------
@pytest.fixture
def fake_panel(monkeypatch):
    class Canvas:
        brightness = 0

    class Matrix:
        def __init__(self, options):
            self.options, self.brightness, self.canvas = options, options.brightness, Canvas()

        def CreateFrameCanvas(self):
            return self.canvas

    class Options:
        pass

    module = types.ModuleType("rgbmatrix")
    module.RGBMatrix, module.RGBMatrixOptions = Matrix, Options
    monkeypatch.setitem(sys.modules, "rgbmatrix", module)


def test_hardware_backend_starts_at_the_configured_brightness_and_changes_live(fake_panel):
    hw = HardwareBackend()
    assert hw.brightness == settings.BRIGHTNESS and hw._matrix.options.brightness == settings.BRIGHTNESS
    hw.set_brightness(35)
    assert hw.brightness == 35 and hw._matrix.brightness == 35 and hw._canvas.brightness == 35
    hw.set_brightness(250)
    assert hw.brightness == 100
    hw.set_brightness(-4)
    assert hw.brightness == 1


def test_hardware_backend_limits_the_app_to_the_configured_cores(fake_panel, monkeypatch):
    seen = []
    monkeypatch.setattr("os.sched_setaffinity", lambda pid, cpus: seen.append((pid, set(cpus))))
    monkeypatch.setattr(settings, "APP_CPUS", (0, 1, 2))
    HardwareBackend()
    assert seen == [(0, {0, 1, 2})]


def test_core_limit_can_be_switched_off_and_failures_are_survived(fake_panel, monkeypatch):
    seen = []
    monkeypatch.setattr("os.sched_setaffinity", lambda pid, cpus: seen.append(cpus))
    monkeypatch.setattr(settings, "APP_CPUS", None)
    HardwareBackend()
    assert seen == []

    def refuse(pid, cpus):
        raise OSError("not permitted")
    monkeypatch.setattr("os.sched_setaffinity", refuse)
    monkeypatch.setattr(settings, "APP_CPUS", (0, 1, 2))
    HardwareBackend()                                          # logs a warning, does not crash


def test_hardware_backend_passes_the_refresh_rate_option(fake_panel, monkeypatch):
    monkeypatch.setattr(settings, "SHOW_REFRESH_RATE", True)
    monkeypatch.setattr(settings, "APP_CPUS", None)
    assert HardwareBackend()._matrix.options.show_refresh_rate is True
