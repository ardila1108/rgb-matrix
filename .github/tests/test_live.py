import pytest
import requests

import routes
import settings
from ledwall.data_sources.live import LiveSource, parse_minutes, validate_routes


class Resp:
    def __init__(self, data=None, status=200):
        self._data, self.status = data, status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")

    def json(self):
        return {"data": self._data}


class FakeApi:
    """Callable standing in for requests.get; answers by (line, stop)."""

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, url, timeout=None):
        line, stop = url.rsplit("/", 2)[-2:]
        self.calls.append((line, stop))
        answer = self.answers[(line, stop)]
        if isinstance(answer, Exception):
            raise answer
        return answer


def data(minutes, unit="minutes"):
    return Resp({"line": "x", "stop": "y", "arrival_time": minutes, "unit": unit})


STOPS = {"304": {"walk_min": 4}, "118": {"walk_min": 3}}
CATS = [
    {"name": "CITY", "buses": [{"line": "24", "stop": "304"}, {"line": "9", "stop": "118"}]},
    {"name": "BEACH", "color": (1, 2, 3), "buses": [{"line": "24", "stop": "304"}]},
]


def source(answers, clock=lambda: 0.0, cats=CATS):
    api = FakeApi(answers)
    return LiveSource(cats, STOPS, get=api, clock=clock), api


def test_pages_built_with_walk_times_and_shared_stop_called_once():
    src, api = source({("24", "304"): data(6), ("9", "118"): data(12)})
    pages = src.fetch_pages()
    assert api.calls.count(("24", "304")) == 1 and len(api.calls) == 2
    assert pages[0] == {"name": "CITY", "buses": [
        {"line": "24", "minutes": 6, "walk_min": 4}, {"line": "9", "minutes": 12, "walk_min": 3}]}
    assert pages[1]["buses"] == [{"line": "24", "minutes": 6, "walk_min": 4}]
    assert pages[1]["color"] == (1, 2, 3)


def test_bus_walk_min_overrides_stop():
    cats = [{"name": "A", "buses": [{"line": "24", "stop": "304", "walk_min": 9}]}]
    src, _ = source({("24", "304"): data(6)}, cats=cats)
    assert src.fetch_pages()[0]["buses"][0]["walk_min"] == 9


def test_parse_minutes_units_and_none():
    assert parse_minutes({"arrival_time": 6, "unit": "minutes"}) == 6
    assert parse_minutes({"arrival_time": 90, "unit": "seconds"}) == 2
    assert parse_minutes({"arrival_time": None, "unit": "minutes"}) is None
    assert parse_minutes({"arrival_time": -1, "unit": "minutes"}) == 0
    with pytest.raises(ValueError):
        parse_minutes({"arrival_time": 5, "unit": "parsecs"})


def test_no_arrival_means_bus_is_left_out():
    src, _ = source({("24", "304"): data(None), ("9", "118"): data(12)})
    pages = src.fetch_pages()
    assert [b["line"] for b in pages[0]["buses"]] == ["9"] and pages[1]["buses"] == []


def test_failed_request_reuses_recent_value_then_drops_it():
    t = [0.0]
    src, api = source({("24", "304"): data(10), ("9", "118"): data(12)}, clock=lambda: t[0])
    src.fetch_pages()
    api.answers[("9", "118")] = requests.ConnectionError("down")
    t[0] = 70.0                                       # inside the reuse window
    pages = src.fetch_pages()
    assert {b["line"]: b["minutes"] for b in pages[0]["buses"]} == {"24": 10, "9": 11}
    t[0] = settings.API_REUSE_SECONDS + 1             # too old
    pages = src.fetch_pages()
    assert [b["line"] for b in pages[0]["buses"]] == ["24"]


def test_http_error_counts_as_failure_and_all_failing_raises():
    src, _ = source({("24", "304"): Resp(status=500), ("9", "118"): requests.Timeout("slow")})
    with pytest.raises(RuntimeError):
        src.fetch_pages()


def test_malformed_payload_is_a_failure_not_a_crash():
    src, _ = source({("24", "304"): Resp({"oops": 1}), ("9", "118"): data(5)})
    pages = src.fetch_pages()
    assert [b["line"] for b in pages[0]["buses"]] == ["9"]


# -- routes.py validation ------------------------------------------------------
def test_shipped_routes_file_is_valid():
    assert validate_routes(routes.CATEGORIES, routes.STOPS) == []


def test_validation_catches_common_mistakes():
    bad = [
        {"name": "WAYTOOLONG", "buses": []},
        {"buses": []},
        {"name": "OK", "buses": [{"line": "24"}, {"line": "9", "stop": "999"},
                                 {"line": "ABCD", "stop": "304"}]},
    ]
    problems = validate_routes(bad, STOPS)
    text = "\n".join(problems)
    assert "longer than 7" in text and "missing 'name'" in text
    assert "needs both" in text and "stop '999'" in text and "'ABCD'" in text
    assert validate_routes([], STOPS) == ["CATEGORIES is empty"]
