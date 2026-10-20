"""Freestyle screen: a 64x64 canvas you sketch on from your phone."""
import io
import logging
import os
import threading
from collections import deque

from PIL import Image, ImageDraw

from .base import Screen

log = logging.getLogger(__name__)

W, H = 64, 64
UNDO_LEVELS = 30
SAVE_DELAY_SECONDS = 1.5


class FreestyleScreen(Screen):
    name = "freestyle"
    label = "Draw"
    icon = "🎨"
    page = "/draw"          # the phone page that edits this screen

    def __init__(self, path=None):
        """`path`: PNG file where the sketch is kept between restarts (None = don't keep)."""
        self._lock = threading.Lock()
        self._img = Image.new("RGB", (W, H), (0, 0, 0))
        self._undo = deque(maxlen=UNDO_LEVELS)
        self._last_stroke = None
        self._path = path
        self._timer = None
        self._load()

    def update(self, data=None):
        pass

    def render(self, now):
        with self._lock:
            return self._img.copy()

    # -- editing ---------------------------------------------------------------
    def _snapshot(self):
        self._undo.append(self._img.copy())

    def draw(self, pixels, stroke=None):
        """pixels: iterable of (x, y, (r, g, b)). Calls with the same `stroke` id undo together."""
        with self._lock:
            if stroke is None or stroke != self._last_stroke:
                self._snapshot()
            self._last_stroke = stroke
            for x, y, color in pixels:
                if 0 <= x < W and 0 <= y < H:
                    self._img.putpixel((x, y), tuple(color))
        self._schedule_save()

    def flood(self, x, y, color):
        """Paint the connected area of one color, like a paint bucket."""
        with self._lock:
            if not (0 <= x < W and 0 <= y < H) or self._img.getpixel((x, y)) == tuple(color):
                return
            self._snapshot()
            self._last_stroke = None
            ImageDraw.floodfill(self._img, (x, y), tuple(color))
        self._schedule_save()

    def clear(self, color=(0, 0, 0)):
        with self._lock:
            self._snapshot()
            self._last_stroke = None
            self._img.paste(tuple(color), (0, 0, W, H))
        self._schedule_save()

    def undo(self):
        with self._lock:
            if not self._undo:
                return False
            self._img = self._undo.pop()
            self._last_stroke = None
        self._schedule_save()
        return True

    def png(self):
        with self._lock:
            buf = io.BytesIO()
            self._img.save(buf, "PNG")
            return buf.getvalue()

    # -- keeping the sketch ------------------------------------------------------
    def _load(self):
        if not self._path or not os.path.exists(self._path):
            return
        try:
            with Image.open(self._path) as saved:
                self._img = saved.convert("RGB").resize((W, H), Image.NEAREST)
        except Exception:
            log.exception("could not load the saved sketch %s", self._path)

    def _schedule_save(self):
        if not self._path:
            return
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(SAVE_DELAY_SECONDS, self.save)
        self._timer.daemon = True
        self._timer.start()

    def save(self):
        if not self._path:
            return
        try:
            os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
            tmp = self._path + ".tmp"
            with self._lock:
                self._img.save(tmp, "PNG")
            os.replace(tmp, self._path)
        except Exception:
            log.exception("could not save the sketch to %s", self._path)
