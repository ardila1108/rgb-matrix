import json
import urllib.error
import urllib.request

import pytest

from ledwall.automation import Automation, build_schedule
from ledwall.control import ControlServer
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen, ClockScreen, FreestyleScreen, HalloweenScreen, TestScreen, WeatherScreen
from tests.test_automation import Clock, Display, KNOWN, at


def call(srv, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{srv.port}{path}", data=data,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class Rig:
    def __init__(self):
        self.when, self.clock = at(9), Clock()                      # 09:00, inside the bus window
        self.manager = ScreenManager([BusScreen(), ClockScreen(), WeatherScreen(), HalloweenScreen(), FreestyleScreen(), TestScreen()])
        self.auto = Automation(build_schedule(KNOWN), self.manager, display=Display(),
                               now=lambda: self.when, clock=self.clock)
        self.srv = ControlServer(self.manager, ("bus", "clock", "weather", "freestyle"), port=0,
                                 host="127.0.0.1", display=Display(), automation=self.auto)
        self.srv.start()

    def tick(self, advance=1.0):
        self.clock.advance(advance)
        self.auto.tick()


@pytest.fixture
def rig():
    r = Rig()
    r.tick()
    yield r
    r.srv.stop()


def test_state_includes_the_automation_status(rig):
    status, state = call(rig.srv, "/api/state")
    assert status == 200
    auto = state["automation"]
    assert auto["enabled"] and auto["plan"] == ["bus"] and auto["until"] == "11:00" and not auto["holding"]
    assert state["active"] == "bus"


def test_picking_a_screen_by_hand_holds_the_schedule(rig):
    status, state = call(rig.srv, "/api/screen", {"name": "clock"})
    assert status == 200 and state["active"] == "clock"
    assert state["automation"]["holding"] and state["automation"]["hold_minutes"] == 30
    rig.tick(600)
    assert rig.manager.active == "clock"                         # the bus window did not take over
    rig.tick(25 * 60)
    assert rig.manager.active == "bus"                           # after the hold


def test_drawing_keeps_the_schedule_away(rig):
    call(rig.srv, "/api/screen", {"name": "freestyle"})
    rig.tick(20 * 60)
    call(rig.srv, "/api/draw", {"pixels": [[1, 1, "#ff0000"]]})   # activity renews the hold
    rig.tick(20 * 60)
    assert rig.manager.active == "freestyle"


def test_turning_automation_off_and_on(rig):
    status, state = call(rig.srv, "/api/automation", {"enabled": False})
    assert status == 200 and state["automation"]["enabled"] is False
    call(rig.srv, "/api/screen", {"name": "weather"})
    rig.tick(24 * 3600)
    assert rig.manager.active == "weather"                       # nothing moves it
    status, state = call(rig.srv, "/api/automation", {"enabled": True})
    assert state["automation"]["enabled"] and not state["automation"]["holding"]
    rig.tick()
    assert rig.manager.active == "bus"                           # schedule is back


def test_resume_button_is_the_same_call_as_enabling(rig):
    call(rig.srv, "/api/screen", {"name": "clock"})
    status, state = call(rig.srv, "/api/automation", {"enabled": True})
    assert not state["automation"]["holding"]
    rig.tick()
    assert rig.manager.active == "bus"


@pytest.mark.parametrize("body", [{"enabled": "yes"}, {"enabled": 1}, {"enabled": None}, {}])
def test_bad_automation_requests_are_refused(rig, body):
    assert call(rig.srv, "/api/automation", body)[0] == 400
    assert rig.auto.enabled


def test_no_automation_means_no_endpoint_and_no_status():
    manager = ScreenManager([BusScreen()])
    srv = ControlServer(manager, ("bus",), port=0, host="127.0.0.1")
    srv.start()
    try:
        assert "automation" not in call(srv, "/api/state")[1]
        assert call(srv, "/api/automation", {"enabled": True})[0] == 404
    finally:
        srv.stop()
