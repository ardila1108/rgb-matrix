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
    assert prepare_pages(p, age_seconds=61)[0].rows[0].minutes == 9
    monkeypatch.setattr(settings, "LOCAL_COUNTDOWN", False)
    assert prepare_pages(p, age_seconds=61)[0].rows[0].minutes == 10


def test_minutes_never_negative():
    rows = prepare_pages([page("A", ("1", 1, 3))], age_seconds=119)[0].rows
    assert rows[0].minutes == 0


def test_buses_further_away_than_the_limit_are_hidden():
    p = [page("A", ("1", 60, 3), ("2", 61, 3), ("3", 90, 3))]
    assert [r.line for r in prepare_pages(p)[0].rows] == ["1"]


def test_limit_is_a_setting_and_cannot_exceed_two_digits(monkeypatch):
    monkeypatch.setattr(settings, "MAX_MINUTES_SHOWN", 30)
    p = [page("A", ("1", 30, 3), ("2", 31, 3))]
    assert [r.line for r in prepare_pages(p)[0].rows] == ["1"]
    monkeypatch.setattr(settings, "MAX_MINUTES_SHOWN", 500)
    p = [page("A", ("1", 99, 3), ("2", 100, 3))]
    assert [r.line for r in prepare_pages(p)[0].rows] == ["1"]


def test_limit_applies_after_the_local_countdown():
    p = [page("A", ("1", 61, 3))]
    assert prepare_pages(p, age_seconds=0) == []
    assert prepare_pages(p, age_seconds=61)[0].rows[0].minutes == 60


def test_page_with_only_far_buses_is_skipped():
    views = prepare_pages([page("A", ("1", 80, 3)), page("B", ("2", 10, 3))])
    assert [v.name for v in views] == ["B"]


def test_leave_now_flag():
    views = prepare_pages([page("A", ("1", 4, 4)), page("B", ("2", 20, 3))])
    assert views[0].has_leave_now and not views[1].has_leave_now


# -- stale data: the numbers can no longer be trusted --------------------------------------
def test_data_older_than_the_stale_limit_has_unknown_times():
    p = [page("A", ("1", 12, 3), ("2", 5, 3))]
    fresh = prepare_pages(p, age_seconds=settings.STALE_AFTER_SECONDS)[0].rows
    assert [r.minutes for r in fresh] != [None, None]
    stale = prepare_pages(p, age_seconds=settings.STALE_AFTER_SECONDS + 1)[0].rows
    assert [r.line for r in stale] == ["2", "1"]                 # same lines, same order
    assert all(r.minutes is None and r.state is State.STALE for r in stale)


def test_a_countdown_never_runs_down_to_zeros_on_old_data():
    p = [page("A", ("1", 3, 3), ("2", 4, 3))]
    for age in (300, 3600, 6 * 3600):
        assert all(r.minutes is None for r in prepare_pages(p, age_seconds=age)[0].rows)


def test_stale_rows_do_not_light_the_page_dots():
    views = prepare_pages([page("A", ("1", 4, 4))], age_seconds=settings.STALE_AFTER_SECONDS + 1)
    assert views[0].alert is None and not views[0].has_leave_now


def test_hidden_far_away_buses_stay_hidden_when_stale():
    p = [page("A", ("1", 90, 3), ("2", 10, 3))]
    rows = prepare_pages(p, age_seconds=settings.STALE_AFTER_SECONDS + 1)[0].rows
    assert [r.line for r in rows] == ["2"]
