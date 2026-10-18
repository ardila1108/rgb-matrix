"""Live data from the dbus-api container.

GET {API_BASE_URL}/api/v1/lines/{line}/{stop}
  -> {"data": {"line": "24", "stop": "304", "arrival_time": 6, "unit": "minutes"}}

Your buses are defined in routes.py. This module turns them into the pages the
bus screen expects.
"""
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor

import requests

import settings
import routes

log = logging.getLogger(__name__)


def validate_routes(categories, stops):
    """Return a list of human-readable problems in routes.py (empty = fine)."""
    problems = []
    if not categories:
        problems.append("CATEGORIES is empty")
    for ci, cat in enumerate(categories, 1):
        name = cat.get("name")
        label = f"category #{ci}" + (f' "{name}"' if name else "")
        if not name or not isinstance(name, str):
            problems.append(f"{label}: missing 'name'")
        elif len(name) > settings.MAX_PAGE_NAME_CHARS:
            problems.append(f"{label}: name is longer than {settings.MAX_PAGE_NAME_CHARS} characters")
        for bi, bus in enumerate(cat.get("buses", []), 1):
            where = f"{label}, bus #{bi}"
            if not bus.get("line") or not bus.get("stop"):
                problems.append(f"{where}: needs both 'line' and 'stop'")
                continue
            if len(str(bus["line"])) > settings.MAX_LINE_CHARS:
                problems.append(f"{where}: line '{bus['line']}' is longer than "
                                f"{settings.MAX_LINE_CHARS} characters and would be cut")
            if "walk_min" not in bus and "walk_min" not in stops.get(str(bus["stop"]), {}):
                problems.append(f"{where}: no walk time; add stop '{bus['stop']}' to STOPS "
                                f"or give the bus a 'walk_min'")
    return problems


def parse_minutes(data):
    """Minutes until arrival from the API's data dict, or None if no bus is coming."""
    value = data.get("arrival_time")
    if value is None:
        return None
    unit = str(data.get("unit") or "minutes").lower()
    if unit.startswith("min"):
        minutes = float(value)
    elif unit.startswith("sec"):
        minutes = math.ceil(float(value) / 60)
    else:
        raise ValueError(f"unsupported unit: {unit!r}")
    return max(0, int(round(minutes)))


def _error_message(response):
    try:
        return str(response.json()["error"]["message"])
    except Exception:
        return ""


class LiveSource:
    def __init__(self, categories=None, stops=None, get=None, clock=time.monotonic):
        self.categories = routes.CATEGORIES if categories is None else categories
        self.stops = routes.STOPS if stops is None else stops
        self._get = get or requests.Session().get
        self._clock = clock
        self._last_good = {}          # (line, stop) -> (minutes, time)
        self._warned = set()          # (line, stop) pairs already reported as unknown

    def _request(self, line, stop):
        url = f"{settings.API_BASE_URL}/api/v1/lines/{line}/{stop}"
        response = self._get(url, timeout=(settings.API_CONNECT_TIMEOUT_SECONDS,
                                            settings.API_TIMEOUT_SECONDS))
        if response.status_code == 404:
            # The API answers 404 "Bus time not found" when no bus is coming. That is
            # an answer, not an outage. Other 404s mean line/stop codes that don't exist.
            message = _error_message(response)
            if "bus time not found" not in message.lower() and (line, stop) not in self._warned:
                self._warned.add((line, stop))
                log.warning("line %s stop %s: %s (check routes.py)", line, stop, message)
            return None
        response.raise_for_status()
        return parse_minutes(response.json()["data"])

    def _safe_request(self, key):
        """('ok', minutes_or_None) or ('error', exception); never raises."""
        try:
            return "ok", self._request(*key)
        except Exception as exc:
            return "error", exc

    def fetch_pages(self):
        keys = sorted({(str(b["line"]), str(b["stop"]))
                       for c in self.categories for b in c.get("buses", [])})
        if not keys:
            return []
        with ThreadPoolExecutor(max_workers=max(1, settings.API_MAX_WORKERS)) as pool:
            outcomes = dict(zip(keys, pool.map(self._safe_request, keys)))
        errors = [(key, value) for key, (status, value) in outcomes.items() if status == "error"]
        if errors:
            key, exc = errors[0]
            log.warning("%d of %d API requests failed (e.g. line %s stop %s: %s)",
                        len(errors), len(keys), key[0], key[1], exc)
        if len(errors) == len(keys):
            raise RuntimeError(f"all {len(keys)} API requests failed")

        now = self._clock()
        minutes = {}
        for key, (status, value) in outcomes.items():
            if status == "ok":
                if value is None:
                    self._last_good.pop(key, None)
                else:
                    self._last_good[key] = (value, now)
                    minutes[key] = value
            elif key in self._last_good:                 # failed: reuse a recent value
                value, when = self._last_good[key]
                age = now - when
                if age <= settings.API_REUSE_SECONDS:
                    minutes[key] = max(0, value - int(age // 60))

        pages = []
        for cat in self.categories:
            buses = []
            for bus in cat.get("buses", []):
                key = (str(bus["line"]), str(bus["stop"]))
                if key not in minutes:
                    continue
                walk = bus.get("walk_min", self.stops.get(key[1], {}).get("walk_min", 0))
                buses.append({"line": key[0], "minutes": minutes[key], "walk_min": walk})
            page = {"name": cat["name"], "buses": buses}
            if cat.get("color"):
                page["color"] = cat["color"]
            pages.append(page)
        return pages


_source = None


def check_routes():
    """Raise a clear error at startup if routes.py is not valid."""
    problems = validate_routes(routes.CATEGORIES, routes.STOPS)
    if problems:
        raise ValueError("routes.py has problems:\n  - " + "\n  - ".join(problems))


def fetch_pages():
    global _source
    if _source is None:
        _source = LiveSource()
    return _source.fetch_pages()
