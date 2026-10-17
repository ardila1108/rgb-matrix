import pytest

import settings
from ledwall.screens.bus_logic import State, classify, prepare_pages


@pytest.mark.parametrize("minutes,walk,expected", [
    (12, 4, State.RELAX),        # slack 8
    (8, 4, State.RELAX),         # slack 4: just above ready window
    (7, 4, State.READY),         # slack 3
    (6, 4, State.READY),         # slack 2
    (5, 4, State.LEAVE),         # slack 1
    (4, 4, State.LEAVE),         # slack 0
    (3, 4, State.RUN),           # slack -1
    (2, 4, State.RUN),           # slack -2
    (3, 5, State.RUN),           # slack -2: still worth running
])
def test_classify_table(minutes, walk, expected):
    assert classify(minutes, walk) is expected


def test_unreachable_below_threshold():
    assert classify(2, 5) is State.UNREACHABLE      # slack -3


@pytest.mark.parametrize("minutes", [1, 0])
def test_gone_beats_everything(minutes):
    assert classify(minutes, 0) is State.GONE
    assert classify(minutes, 5) is State.GONE


def test_walk_time_changes_color_for_same_minutes():
    assert classify(9, 3) is State.RELAX
    assert classify(9, 8) is State.LEAVE


def page(name, *buses):
    return {"name": name, "buses": [
        {"line": l, "minutes": m, "walk_min": w} for l, m, w in buses]}


def test_rows_sorted_and_capped_at_three():
    views = prepare_pages([page("CITY", ("1", 20, 3), ("2", 5, 3), ("3", 12, 3), ("4", 7, 3))])
    assert [r.line for r in views[0].rows] == ["2", "4", "3"]


def test_empty_pages_skipped_and_colors_stay_stable():
    views = prepare_pages([page("A"), page("B", ("1", 9, 3))])
    assert [v.name for v in views] == ["B"]
    assert views[0].color == settings.PAGE_COLORS[1]


def test_explicit_page_color_wins():
    p = page("A", ("1", 9, 3)) | {"color": (1, 2, 3)}
    assert prepare_pages([p])[0].color == (1, 2, 3)


def test_malformed_entries_are_skipped():
    p = {"name": "X", "buses": [{"line": "1"}, {"line": "2", "minutes": "soon"},
                                {"line": "3", "minutes": 8, "walk_min": 3}]}
    views = prepare_pages([p, "garbage", None])
    assert [r.line for r in views[0].rows] == ["3"]


def test_names_and_lines_are_truncated_and_uppercased():
    views = prepare_pages([page("city center", ("n3x9", 9, 3))])
    assert views[0].name == "CITY CE"
    assert views[0].rows[0].line == "N3X"


def test_local_countdown(monkeypatch):
    p = [page("A", ("1", 10, 3))]
    assert prepare_pages(p, age_seconds=59)[0].rows[0].minutes == 10
    assert prepare_pages(p, age_seconds=125)[0].rows[0].minutes == 8
    monkeypatch.setattr(settings, "LOCAL_COUNTDOWN", False)
    assert prepare_pages(p, age_seconds=125)[0].rows[0].minutes == 10


def test_minutes_never_negative_and_capped_at_99():
    p = [page("A", ("1", 1, 3), ("2", 250, 3))]
    rows = prepare_pages(p, age_seconds=600)[0].rows
    assert rows[0].minutes == 0 and rows[1].minutes == 99


def test_leave_now_flag():
    views = prepare_pages([page("A", ("1", 4, 4)), page("B", ("2", 20, 3))])
    assert views[0].has_leave_now and not views[1].has_leave_now
