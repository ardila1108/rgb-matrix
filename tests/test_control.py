import json
import urllib.error
import urllib.request

import pytest

from ledwall.control import ControlServer
from ledwall.manager import ScreenManager
from ledwall.screens import BusScreen, ClockScreen, FreestyleScreen, TestScreen


@pytest.fixture
def server():
    manager = ScreenManager([BusScreen(), ClockScreen(), FreestyleScreen(), TestScreen()], active="bus")
    srv = ControlServer(manager, ("bus", "clock", "freestyle"), port=0, host="127.0.0.1")
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
    assert [s["name"] for s in state["screens"]] == ["bus", "clock", "freestyle"]
    assert state["screens"][1] == {"name": "clock", "label": "Clock", "icon": "🕒"}
    assert state["screens"][2]["page"] == "/draw"              # only screens with a page have one


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


# -- sketching -------------------------------------------------------------------
def sketch(manager):
    return manager.get("freestyle")


def test_draw_page_and_canvas_png_are_served(server):
    srv, _ = server
    status, body = call(srv, "/draw")
    assert status == 200 and b"/api/draw" in body
    status, body = call(srv, "/api/draw/canvas.png?123")
    assert status == 200 and body.startswith(b"\x89PNG")


def test_drawing_over_the_api_changes_the_canvas(server):
    srv, manager = server
    status, _ = call(srv, "/api/draw", {"stroke": 1, "pixels": [[3, 4, "#ff0000"], [5, 6, "#00FF00"]]})
    assert status == 200
    img = sketch(manager).render(0.0)
    assert img.getpixel((3, 4)) == (255, 0, 0) and img.getpixel((5, 6)) == (0, 255, 0)


def test_fill_clear_and_undo_over_the_api(server):
    srv, manager = server
    call(srv, "/api/draw/fill", {"x": 0, "y": 0, "color": "#0000ff"})
    assert sketch(manager).render(0.0).getpixel((30, 30)) == (0, 0, 255)
    status, body = call(srv, "/api/draw/undo", {})
    assert status == 200 and json.loads(body)["undone"] is True
    assert sketch(manager).render(0.0).getpixel((30, 30)) == (0, 0, 0)
    call(srv, "/api/draw", {"pixels": [[1, 1, "#ffffff"]]})
    call(srv, "/api/draw/clear", {})
    assert sketch(manager).render(0.0).getpixel((1, 1)) == (0, 0, 0)


@pytest.mark.parametrize("body", [
    {"pixels": [[64, 0, "#ff0000"]]},            # outside the grid
    {"pixels": [[0, 0, "red"]]},                 # not a hex color
    {"pixels": [[0, 0]]},                        # too short
    {"pixels": [["0", 0, "#ff0000"]]},           # not a number
    {"pixels": "nope"},
    {"pixels": [[0, 0, "#ff0000"]] * 4097},      # too many
    {},
])
def test_bad_pixels_are_refused_and_change_nothing(server, body):
    srv, manager = server
    assert call(srv, "/api/draw", body)[0] == 400
    assert sketch(manager).render(0.0).getcolors() == [(4096, (0, 0, 0))]


def test_bad_fill_requests_are_refused(server):
    srv, _ = server
    assert call(srv, "/api/draw/fill", {"x": 99, "y": 0, "color": "#ffffff"})[0] == 400
    assert call(srv, "/api/draw/fill", {"x": 1, "y": 0, "color": "white"})[0] == 400
    assert call(srv, "/api/draw/fill", {"x": True, "y": 0, "color": "#ffffff"})[0] == 400


def test_oversized_body_is_refused(server):
    srv, _ = server
    assert call(srv, "/api/draw", raw=b"{" + b" " * (200 * 1024) + b"}")[0] == 400


def test_draw_routes_do_not_exist_without_the_freestyle_screen():
    manager = ScreenManager([BusScreen(), ClockScreen()], active="bus")
    srv = ControlServer(manager, ("bus", "clock"), port=0, host="127.0.0.1")
    srv.start()
    try:
        assert call(srv, "/draw")[0] == 404
        assert call(srv, "/api/draw", {"pixels": []})[0] == 404
    finally:
        srv.stop()
