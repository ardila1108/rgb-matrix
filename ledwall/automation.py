"""Automation: which screen is shown, and how bright it is, by time of day.

Configured in settings.py (SCREEN_SCHEDULE, DEFAULT_SCREENS, BRIGHTNESS_SCHEDULE).
"""
import logging
import math
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import settings

log = logging.getLogger(__name__)

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_HHMM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
MAX_LOOKAHEAD_MINUTES = 36 * 60


def parse_hhmm(text):
    """'08:30' -> minutes since midnight."""
    match = _HHMM.match(str(text).strip())
    if not match:
        raise ValueError(f'{text!r} is not a time like "08:30"')
    return int(match.group(1)) * 60 + int(match.group(2))


@dataclass(frozen=True)
class Window:
    start: int                       # minutes since midnight, included
    end: int                         # excluded; a window may cross midnight
    days: frozenset = None           # weekday numbers (Monday = 0); None = every day
    screens: tuple = None            # ((name, seconds), ...) for screen windows
    brightness: int = None           # for brightness windows

    def active(self, moment):
        minute = moment.hour * 60 + moment.minute
        day = moment.weekday()
        if self.start < self.end:
            inside = self.start <= minute < self.end
        elif minute >= self.start:                      # crosses midnight, evening part
            inside = True
        elif minute < self.end:                         # ... and the morning part
            inside, day = True, (day - 1) % 7           # belongs to the day it started
        else:
            inside = False
        return inside and (self.days is None or day in self.days)


def _parse_days(raw, where, problems):
    if raw is None:
        return None
    days = set()
    for item in raw:
        name = str(item).strip().lower()[:3]
        if name not in DAYS:
            problems.append(f'{where}: unknown day {item!r} (use mon, tue, wed, thu, fri, sat, sun)')
        else:
            days.add(DAYS.index(name))
    return frozenset(days)


def _parse_times(entry, where, problems):
    try:
        start, end = parse_hhmm(entry.get("from")), parse_hhmm(entry.get("to"))
    except ValueError as exc:
        problems.append(f'{where}: {exc} ("from" and "to" are required)')
        return None
    if start == end:
        problems.append(f'{where}: "from" and "to" are the same time')
        return None
    return start, end


def _parse_screens(raw, default_seconds, where, problems):
    items = []
    if not raw:
        problems.append(f'{where}: "screens" needs at least one screen')
        return None
    for item in raw:
        name, seconds = (item, default_seconds) if isinstance(item, str) else (item[0], item[1])
        if not isinstance(name, str) or not isinstance(seconds, (int, float)) or seconds <= 0:
            problems.append(f'{where}: bad screen entry {item!r} (use "clock" or ("clock", 30))')
            return None
        items.append((name, float(seconds)))
    return tuple(items)


class Schedule:
    def __init__(self, screen_windows, brightness_windows, default_screens, base_brightness):
        self.screen_windows = screen_windows
        self.brightness_windows = brightness_windows
        self.default_screens = default_screens
        self.base_brightness = base_brightness

    def plan_at(self, moment):
        """((name, seconds), ...) to show at this moment. First matching window wins."""
        for window in self.screen_windows:
            if window.active(moment):
                return window.screens
        return self.default_screens

    def brightness_at(self, moment):
        for window in self.brightness_windows:
            if window.active(moment):
                return window.brightness
        return self.base_brightness

    def screen_names(self):
        names = {n for n, _ in self.default_screens}
        for window in self.screen_windows:
            names.update(n for n, _ in window.screens)
        return names


def build_schedule(known_screens=None, cfg=settings):
    """Read the schedule from settings. Raises ValueError listing every mistake."""
    problems = []
    rotation = getattr(cfg, "ROTATION_SECONDS", 20)
    if not isinstance(rotation, (int, float)) or rotation <= 0:
        problems.append("ROTATION_SECONDS must be a positive number")
        rotation = 20

    default_screens = _parse_screens(cfg.DEFAULT_SCREENS, rotation, "DEFAULT_SCREENS", problems)

    screen_windows = []
    for i, entry in enumerate(cfg.SCREEN_SCHEDULE, 1):
        where = f"SCREEN_SCHEDULE entry #{i}"
        times = _parse_times(entry, where, problems)
        seconds = entry.get("seconds", rotation)
        screens = _parse_screens(entry.get("screens"), seconds, where, problems)
        days = _parse_days(entry.get("days"), where, problems)
        if times and screens:
            screen_windows.append(Window(times[0], times[1], days, screens=screens))

    brightness_windows = []
    for i, entry in enumerate(cfg.BRIGHTNESS_SCHEDULE, 1):
        where = f"BRIGHTNESS_SCHEDULE entry #{i}"
        times = _parse_times(entry, where, problems)
        level = entry.get("brightness")
        if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 100:
            problems.append(f'{where}: "brightness" must be a whole number from 1 to 100')
            level = None
        days = _parse_days(entry.get("days"), where, problems)
        if times and level:
            brightness_windows.append(Window(times[0], times[1], days, brightness=level))

    schedule = Schedule(screen_windows, brightness_windows, default_screens or (), cfg.BRIGHTNESS)
    if known_screens is not None:
        for name in sorted(schedule.screen_names() - set(known_screens)):
            problems.append(f"unknown screen {name!r} in the schedule (known: {', '.join(sorted(known_screens))})")
    if problems:
        raise ValueError("schedule has problems:\n  - " + "\n  - ".join(problems))
    return schedule


class Automation:
    """Switches screens and brightness by the schedule, unless you take over by hand."""

    def __init__(self, schedule, manager, display=None, enabled=True, now=None, clock=time.monotonic):
        self._schedule, self._manager, self._display = schedule, manager, display
        self._enabled = enabled
        self._now = now or (lambda: datetime.now(ZoneInfo(settings.TIMEZONE)))
        self._clock = clock
        self._lock = threading.Lock()
        self._hold_until = None
        self._plan = None
        self._plan_start = 0.0
        self._brightness_target = None
        self._last_tick = -1e9
        self._until_cache = None

    # -- called every frame by the main loop -----------------------------------------
    def tick(self):
        with self._lock:
            if not self._enabled:
                return
            mono = self._clock()
            if mono - self._last_tick < 0.2:
                return
            self._last_tick = mono
            moment = self._now()

            if self._display is not None:
                target = self._schedule.brightness_at(moment)
                if target != self._brightness_target:      # only at changes: a slider move sticks
                    self._brightness_target = target
                    self._display.set_brightness(target)
                    log.info("brightness set to %d%% by the schedule", target)

            if self._hold_until is not None:
                if mono < self._hold_until:
                    return
                self._hold_until, self._plan = None, None  # hold is over: pick up the schedule
                log.info("manual hold ended, automation resumes")

            plan = self._schedule.plan_at(moment)
            if plan != self._plan:
                self._plan, self._plan_start = plan, mono
            name = self._pick(plan, mono - self._plan_start)
            if name != self._manager.active:
                self._manager.set_active(name)

    @staticmethod
    def _pick(plan, elapsed):
        if len(plan) == 1:
            return plan[0][0]
        position = elapsed % sum(seconds for _, seconds in plan)
        for name, seconds in plan:
            if position < seconds:
                return name
            position -= seconds
        return plan[-1][0]

    # -- called from the phone page --------------------------------------------------
    def hold(self):
        """You picked a screen by hand: automation waits MANUAL_HOLD_MINUTES."""
        with self._lock:
            if not self._enabled:
                return
            minutes = settings.MANUAL_HOLD_MINUTES
            self._hold_until = math.inf if not minutes else self._clock() + minutes * 60

    def set_enabled(self, enabled):
        with self._lock:
            self._enabled = bool(enabled)
            self._hold_until = None
            self._plan = None
            self._brightness_target = None              # re-apply the scheduled brightness
            self._last_tick = -1e9
            self._until_cache = None
        log.info("automation %s", "on" if enabled else "off")

    @property
    def enabled(self):
        return self._enabled

    def status(self):
        with self._lock:
            mono, moment = self._clock(), self._now()
            holding = self._hold_until is not None and mono < self._hold_until
            plan = self._schedule.plan_at(moment)
            seconds = {s for _, s in plan}
            status = {
                "enabled": self._enabled,
                "holding": holding,
                "hold_minutes": None if not holding or self._hold_until == math.inf
                else max(1, math.ceil((self._hold_until - mono) / 60)),
                "plan": [name for name, _ in plan],
                "rotating": len(plan) > 1,
                "seconds": int(seconds.pop()) if len(seconds) == 1 else None,
                "until": self._next_change(moment, plan) if self._enabled and not holding else None,
            }
            return status

    def _next_change(self, moment, plan):
        key = (moment.replace(second=0, microsecond=0), plan)
        if self._until_cache and self._until_cache[0] == key:
            return self._until_cache[1]
        text = None
        probe = moment.replace(second=0, microsecond=0)
        for _ in range(MAX_LOOKAHEAD_MINUTES):
            probe += timedelta(minutes=1)
            if self._schedule.plan_at(probe) != plan:
                text = probe.strftime("%H:%M" if probe.date() == moment.date() else "%a %H:%M")
                break
        self._until_cache = (key, text)
        return text
