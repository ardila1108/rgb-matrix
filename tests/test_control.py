import json
import urllib.error
import urllib.request

import pytest

from ledwall.control import ControlServer
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen, ClockScreen, TestScreen


@pytest.fixture
def server():
    manager = ScreenManager([BusScreen(), ClockScreen(), TestScreen()], active="bus")
    srv = ControlServer(manager, ("bus", "clock"), port=0, host="127.0.0.1")
    srv.start()
    yield srv, manager
    srv.stop()


def call(srv, path, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(f"http://127.0.0.1:{srv.port}{path}", data=data,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_state_lists_menu_screens_only(server):
    srv, _ = server
    status, body = call(srv, "/api/state")
    state = json.loads(body)
    assert status == 200 and state["active"] == "bus"
    assert [s["name"] for s in state["screens"]] == ["bus", "clock"]
    assert state["screens"][1] == {"name": "clock", "label": "Clock", "icon": "🕒"}


def test_switching_changes_the_active_screen(server):
    srv, manager = server
    status, body = call(srv, "/api/screen", {"name": "clock"})
    assert status == 200 and json.loads(body)["active"] == "clock"
    assert manager.active == "clock"
    call(srv, "/api/screen", {"name": "bus"})
    assert manager.active == "bus"


def test_screens_outside_the_menu_and_unknown_ones_are_refused(server):
    srv, manager = server
    assert call(srv, "/api/screen", {"name": "test"})[0] == 404
    assert call(srv, "/api/screen", {"name": "nope"})[0] == 404
    assert manager.active == "bus"


@pytest.mark.parametrize("raw", [b"not json", b"{}", b'{"name": 5}', b"[]"])
def test_bad_requests_get_400_and_change_nothing(server, raw):
    srv, manager = server
    assert call(srv, "/api/screen", raw=raw)[0] in (400, 404)
    assert manager.active == "bus"


def test_page_is_served_and_unknown_paths_404(server):
    srv, _ = server
    status, body = call(srv, "/")
    assert status == 200 and b"LED Wall" in body
    assert call(srv, "/nope")[0] == 404
