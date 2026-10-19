import threading
import time

from PIL import Image, ImageDraw

import settings
from .. import font
from .base import Screen
from .bus_logic import State, prepare_pages, ROWS_PER_PAGE

W, H = 64, 64
HEADER_TEXT_X, HEADER_TEXT_Y = 8, 1
PROGRESS_Y = 10
ROW_Y0, ROW_PITCH = 12, 17
OFF_LINE = (28, 28, 28)
BLACK = (0, 0, 0)


def _state_colors():
    return {
        State.RELAX: settings.COLOR_RELAX,
        State.READY: settings.COLOR_READY,
        State.LEAVE: settings.COLOR_LEAVE,
        State.RUN: settings.COLOR_RUN,
        State.GONE: settings.COLOR_GONE,
        State.UNREACHABLE: settings.COLOR_UNREACHABLE,
    }


class BusScreen(Screen):
    """Pages of buses grouped by destination, with walk-time-aware colors."""

    name = "bus"
    label = "Buses"
    icon = "🚌"

    def __init__(self):
        self._lock = threading.Lock()
        self._pages = None
        self._received = None
        self._cur = None          # name of the page on screen
        self._page_start = 0.0
        self._trans = None        # {"t0", "src", "dst"} while sliding

    # -- data in ------------------------------------------------------------
    def update(self, data, now=None):
        """data: list of page dicts (see bus_logic.prepare_pages)."""
        with self._lock:
            self._pages = data
            self._received = time.monotonic() if now is None else now

    # -- frame out ----------------------------------------------------------
    def render(self, now):
        with self._lock:
            pages, received = self._pages, self._received
        if received is None:
            return self._message("LOADING")
        age = now - received
        views = prepare_pages(pages, age)
        if not views:
            return self._message("NO BUS")

        stale = age > settings.STALE_AFTER_SECONDS
        blink = int(now * 2) % 2 == 0
        names = [v.name for v in views]

        if self._cur not in names:
            self._cur, self._page_start, self._trans = names[0], now, None

        def page(name, progress):
            return self._page_image(views, names.index(name), progress, blink, stale)

        if self._trans:
            frac = (now - self._trans["t0"]) / max(settings.TRANSITION_SECONDS, 0.001)
            src, dst = self._trans["src"], self._trans["dst"]
            if src not in names or dst not in names:
                self._trans = None
            elif frac >= 1:
                self._cur, self._page_start, self._trans = dst, now, None
            else:
                return self._slide(page(src, 1.0), page(dst, 0.0), frac)

        if len(views) > 1 and now - self._page_start >= settings.DWELL_SECONDS:
            nxt = names[(names.index(self._cur) + 1) % len(names)]
            self._trans = {"t0": now, "src": self._cur, "dst": nxt}
            return page(self._cur, 1.0)

        progress = 0.0
        if len(views) > 1:
            progress = min(1.0, (now - self._page_start) / settings.DWELL_SECONDS)
        return page(self._cur, progress)

    # -- drawing ------------------------------------------------------------
    def _message(self, text):
        img = Image.new("RGB", (W, H), BLACK)
        d = ImageDraw.Draw(img)
        x = (W - font.text_width(text)) // 2
        font.draw_text(d, text, x, 28, settings.COLOR_UNREACHABLE)
        return img

    @staticmethod
    def _slide(a, b, frac):
        shift = max(0, min(W, int(frac * W)))
        out = Image.new("RGB", (W, H), BLACK)
        out.paste(a.crop((shift, 0, W, H)), (0, 0))
        out.paste(b.crop((0, 0, shift, H)), (W - shift, 0))
        return out

    def _page_image(self, views, idx, progress, blink, stale):
        view = views[idx]
        colors = _state_colors()
        img = Image.new("RGB", (W, H), BLACK)
        d = ImageDraw.Draw(img)

        # header: arrow, destination, page dots
        font.draw_bitmap(d, font.ARROW, 1, 2, view.color)
        font.draw_text(d, view.name, HEADER_TEXT_X, HEADER_TEXT_Y, settings.COLOR_TEXT)
        n = min(len(views), 8)
        pitch, size = (3, 2) if n <= 5 else (2, 1)
        x0, y0 = W - n * pitch, 3 if size == 2 else 4
        for i in range(n):
            alert = views[i].alert
            if i == idx:
                c = settings.COLOR_TEXT
            elif alert is not None and (blink or not settings.DOT_BLINK):
                c = colors[alert]
            else:
                c = settings.COLOR_DOT_OFF
            x = x0 + i * pitch
            d.rectangle([x, y0, x + size - 1, y0 + size - 1], fill=c)

        # progress line toward the next page (dim red when data is stale)
        filled = round(progress * W)
        for x in range(W):
            if stale:
                c = settings.COLOR_STALE
            else:
                c = view.color if x < filled else OFF_LINE
            d.point((x, PROGRESS_Y), fill=c)

        # bus rows
        for i, row in enumerate(view.rows[:ROWS_PER_PAGE]):
            t = ROW_Y0 + i * ROW_PITCH
            d.rectangle([1, t + 2, 21, t + 14], fill=settings.COLOR_BADGE)
            for cx, cy in ((1, t + 2), (21, t + 2), (1, t + 14), (21, t + 14)):
                d.point((cx, cy), fill=BLACK)
            bx = 1 + (21 - font.text_width(row.line)) // 2
            font.draw_text(d, row.line, bx, t + 5, settings.COLOR_TEXT)

            if row.state is not State.GONE or blink:
                s = str(row.minutes)
                font.draw_text(d, s, 48 - len(s) * 12 + 2, t + 1,
                               colors[row.state], sx=2, sy=2)
            font.draw_bitmap(d, font.UNIT_M, 51, t + 11, settings.COLOR_UNIT)
        return img
