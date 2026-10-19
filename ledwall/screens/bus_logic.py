"""Pure bus-screen logic: no drawing, no time, easy to unit test."""
import logging
from dataclasses import dataclass
from enum import Enum

import settings

log = logging.getLogger(__name__)

ROWS_PER_PAGE = 3      # fixed by the 64x64 layout
MAX_DISPLAYABLE = 99   # two digits on the panel


class State(Enum):
    RELAX = "relax"              # green
    READY = "ready"              # amber
    LEAVE = "leave"              # violet: last chance without running
    RUN = "run"                  # orange: only if you run
    GONE = "gone"                # red, blinking
    UNREACHABLE = "unreachable"  # gray: you can't make it


@dataclass(frozen=True)
class Row:
    line: str
    minutes: int
    state: State


@dataclass(frozen=True)
class PageView:
    name: str
    color: tuple
    rows: list

    @property
    def has_leave_now(self):
        return any(r.state is State.LEAVE for r in self.rows)

    @property
    def has_gone(self):
        return any(r.state is State.GONE for r in self.rows)

    @property
    def alert(self):
        """State shown on this page's dot: the first of settings.DOT_PRIORITY present, else None."""
        present = {r.state for r in self.rows}
        for name in settings.DOT_PRIORITY:
            state = State(name)
            if state in present:
                return state
        return None


def classify(minutes, walk_min):
    """Urgency of a bus given minutes left and the walk to its stop."""
    if minutes <= settings.GONE_MINUTES:
        return State.GONE
    slack = minutes - walk_min
    if slack < settings.UNREACHABLE_SLACK:
        return State.UNREACHABLE
    if slack < settings.LEAVE_NOW_SLACK[0]:
        return State.RUN
    if slack <= settings.LEAVE_NOW_SLACK[1]:
        return State.LEAVE
    if slack <= settings.GET_READY_SLACK[1]:
        return State.READY
    return State.RELAX


def prepare_pages(pages, age_seconds=0.0):
    """Turn raw pages into what the screen draws.

    pages: [{"name": "CITY", "color": (r,g,b) optional,
             "buses": [{"line": "24", "minutes": 12, "walk_min": 4}, ...]}, ...]
    age_seconds: how old the snapshot is (for the local countdown).
    Buses further away than settings.MAX_MINUTES_SHOWN are hidden. Empty pages are
    dropped; each page keeps its soonest 3 buses.
    """
    elapsed = int(age_seconds // 60) if settings.LOCAL_COUNTDOWN else 0
    limit = min(settings.MAX_MINUTES_SHOWN, MAX_DISPLAYABLE)
    views = []
    for i, page in enumerate(pages or []):
        if not isinstance(page, dict):
            log.warning("skipping malformed page: %r", page)
            continue
        rows = []
        for bus in page.get("buses") or []:
            try:
                minutes = max(0, int(bus["minutes"]) - elapsed)
                walk = int(bus.get("walk_min", 0))
                line = str(bus["line"]).upper()[: settings.MAX_LINE_CHARS]
            except (KeyError, TypeError, ValueError, AttributeError):
                log.warning("skipping malformed bus entry: %r", bus)
                continue
            if minutes > limit:
                continue                      # too far away to be interesting
            rows.append(Row(line, minutes, classify(minutes, walk)))
        if not rows:
            continue
        rows.sort(key=lambda r: r.minutes)
        palette = settings.PAGE_COLORS
        color = tuple(page.get("color") or palette[i % len(palette)])
        name = str(page.get("name", "")).upper()[: settings.MAX_PAGE_NAME_CHARS]
        views.append(PageView(name, color, rows[:ROWS_PER_PAGE]))
    return views
