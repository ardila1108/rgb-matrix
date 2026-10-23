import json
import urllib.error
import urllib.request

import pytest

from ledwall.automation import Automation, build_schedule
from ledwall.control import ControlServer
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen, ClockScreen
from tests.test_automation import KNOWN, Clock, Display, at
from tests.test_automation_control import Rig, call


@pytest.fixture
def rig():
    r = Rig()
    r.tick()
    yield r
    r.srv.stop()


def test_pinning_over_the_api(rig):
    status, state = call(rig.srv, "/api/pin", {"name": "weather"})
    assert status == 200 and state["active"] == "weather" and state["automation"]["pinned"] == "weather"
    rig.tick(3 * 3600)
    assert rig.manager.active == "weather"
    assert call(rig.srv, "/api/state")[1]["automation"]["pinned"] == "weather"


def test_unpinning_over_the_api(rig):
    call(rig.srv, "/api/pin", {"name": "weather"})
    status, state = call(rig.srv, "/api/pin", {"name": None})
    assert status == 200 and state["automation"]["pinned"] is None
    rig.tick()
    assert rig.manager.active == "bus"                         # 09:00 bus window


def test_screens_outside_the_menu_cannot_be_pinned(rig):
    assert call(rig.srv, "/api/pin", {"name": "test"})[0] == 404
    assert call(rig.srv, "/api/pin", {"name": "radio"})[0] == 404
    assert rig.auto.pinned is None


@pytest.mark.parametrize("body", [{}, {"name": 5}, {"name": ["clock"]}, {"pin": "clock"}])
def test_bad_pin_requests_are_refused(rig, body):
    assert call(rig.srv, "/api/pin", body)[0] == 400
    assert rig.auto.pinned is None


def test_tapping_another_screen_while_pinned_is_a_temporary_peek(rig):
    call(rig.srv, "/api/pin", {"name": "clock"})
    status, state = call(rig.srv, "/api/screen", {"name": "weather"})
    assert state["active"] == "weather" and state["automation"]["holding"]
    assert state["automation"]["pinned"] == "clock"            # the pin is still there
    rig.tick(31 * 60)
    assert rig.manager.active == "clock"


def test_no_automation_means_no_pin_endpoint():
    srv = ControlServer(ScreenManager([BusScreen(), ClockScreen()]), ("bus", "clock"), port=0, host="127.0.0.1")
    srv.start()
    try:
        assert call(srv, "/api/pin", {"name": "clock"})[0] == 404
    finally:
        srv.stop()
