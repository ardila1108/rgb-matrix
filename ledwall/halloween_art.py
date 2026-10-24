"""Pixel art for the Halloween screen. Drawn with code so it can grow, fade and move."""
import math

from PIL import Image, ImageDraw

W, H = 64, 64
GROUND_Y = 57

SKY_TOP = (4, 2, 16)
SKY_LOW = (34, 10, 46)
ORANGE = (255, 110, 0)
ORANGE_D = (190, 70, 0)
STEM = (40, 150, 40)
GLOW = (255, 215, 60)
GLOW_D = (255, 140, 20)
GHOST = (225, 230, 255)
BONE = (235, 232, 215)
BAT = (125, 60, 165)
BAT_EYE = (255, 50, 50)
MOON = (255, 214, 140)
MOON_CRATER = (222, 170, 100)
MOON_HALO = (44, 28, 44)
TOMB = (80, 80, 100)
TOMB_HI = (112, 112, 134)
TOMB_DARK = (45, 45, 60)
GROUND = (14, 7, 18)
GROUND_EDGE = (34, 18, 44)
SPIDER = (130, 130, 160)
THREAD = (80, 80, 105)
STAR = (190, 190, 255)
EYES_YELLOW = (255, 230, 0)
EYES_GREEN = (90, 255, 90)
PURPLE_TEXT = (175, 95, 255)
RED = (255, 50, 40)

STARS = [(5, 4), (17, 9), (28, 3), (39, 8), (56, 5), (61, 17), (9, 21), (47, 26), (24, 27)]

_sky = None


def scale(color, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(c * k) for c in color)


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def sky():
    """A fresh copy of the night sky (a dark gradient, cached)."""
    global _sky
    if _sky is None:
        _sky = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(_sky)
        for y in range(H):
            k = (y / (H - 1)) ** 1.5
            d.line([(0, y), (W - 1, y)], fill=tuple(round(a + (b - a) * k) for a, b in zip(SKY_TOP, SKY_LOW)))
    return _sky.copy()


def stars(d, tick):
    for i, (x, y) in enumerate(STARS):
        if (tick // 2 + i) % 3 != 0:
            d.point((x, y), fill=STAR)


def ground(d):
    d.rectangle([0, GROUND_Y, W - 1, H - 1], fill=GROUND)
    d.line([(0, GROUND_Y), (W - 1, GROUND_Y)], fill=GROUND_EDGE)
    for x in range(1, W, 5):
        d.point((x, GROUND_Y - 1), fill=GROUND_EDGE)
        d.point((x + 1, GROUND_Y - 2), fill=GROUND_EDGE)


def disc(d, cx, cy, r, color):
    for y in range(-int(r), int(r) + 1):
        for x in range(-int(r), int(r) + 1):
            if x * x + y * y <= r * r + 0.5:
                d.point((cx + x, cy + y), fill=color)


def moon(d, cx, cy, r):
    disc(d, cx, cy, r + 2, MOON_HALO)
    disc(d, cx, cy, r, MOON)
    c = max(1, r // 4)
    disc(d, cx - r // 3, cy - r // 4, c, MOON_CRATER)
    disc(d, cx + r // 3, cy + r // 5, max(1, c - 1), MOON_CRATER)
    disc(d, cx - r // 6, cy + r // 2, max(1, c - 1), MOON_CRATER)


def pumpkin(d, cx, cy, grow=1.0, tick=0, small=False, seed=0):
    """A jack-o'-lantern. `grow` 0..1 makes it pop up; the candle flickers with `tick`."""
    if grow < 0.05:
        return
    rx, ry = ((4.5, 4.0) if small else (7.5, 6.5))
    rx, ry = rx * grow, ry * grow
    for y in range(-int(ry) - 1, int(ry) + 2):
        for x in range(-int(rx) - 1, int(rx) + 2):
            if (x / rx) ** 2 + (y / ry) ** 2 <= 1.0:
                ridge = abs(x) == (2 if small else 3) or (not small and abs(x) == 6 and abs(y) < 3)
                d.point((cx + x, cy + y), fill=ORANGE_D if ridge else ORANGE)
    if grow > 0.6:
        top = cy - int(ry)
        if small:
            d.line([(cx, top - 2), (cx, top)], fill=STEM)
        else:
            d.rectangle([cx - 1, top - 3, cx, top], fill=STEM)
            d.point((cx + 1, top - 3), fill=STEM)
    if grow > 0.8:
        glow = GLOW_D if (tick + seed) % 4 == 0 else GLOW
        if small:
            cells = [(-2, -1), (2, -1), (-2, 1), (-1, 2), (0, 2), (1, 2), (2, 1)]
        else:
            cells = [(-4, -2), (-3, -2), (-2, -2), (-3, -3), (2, -2), (3, -2), (4, -2), (3, -3),
                     (0, 0), (-1, 1), (0, 1), (1, 1)]
            cells += [(x, 3) for x in range(-4, 5)] + [(x, 4) for x in range(-3, 4)]
        for x, y in cells:
            d.point((cx + x, cy + y), fill=glow)
        if not small:
            for x, y in [(-2, 3), (2, 3), (0, 4)]:                      # the teeth
                d.point((cx + x, cy + y), fill=ORANGE)


def ghost(d, cx, cy, alpha=1.0):
    """A floating ghost about 13 x 15 pixels. `alpha` fades it in and out."""
    if alpha <= 0.02:
        return
    body, shade = scale(GHOST, alpha), scale(GHOST, alpha * 0.82)
    left, top = cx - 6, cy - 7
    for y in range(15):
        for x in range(13):
            if y < 6:
                inside = (x - 6) ** 2 + (y - 6) ** 2 <= 36
            elif y <= 12:
                inside = True
            elif y == 13:
                inside = True
            else:
                inside = x % 4 < 2
            if inside:
                d.point((left + x, top + y), fill=shade if (y > 10 or x in (0, 12)) else body)
    d.rectangle([left + 3, top + 5, left + 4, top + 7], fill=(0, 0, 0))
    d.rectangle([left + 8, top + 5, left + 9, top + 7], fill=(0, 0, 0))
    d.rectangle([left + 5, top + 9, left + 7, top + 10], fill=(0, 0, 0))


_WING_UP = [(-2, -1), (-3, -2), (-4, -2), (-5, -3), (-6, -3)]
_WING_DOWN = [(-2, 0), (-3, 1), (-4, 1), (-5, 1), (-6, 0)]


def bat(d, cx, cy, flap):
    wing = _WING_UP if flap % 2 == 0 else _WING_DOWN
    for x, y in wing:
        d.point((cx + x, cy + y), fill=BAT)
        d.point((cx - x, cy + y), fill=BAT)
    for x, y in [(0, 0), (0, 1), (-1, -1), (1, -1)]:
        d.point((cx + x, cy + y), fill=BAT)
    d.point((cx - 1, cy), fill=BAT_EYE)
    d.point((cx + 1, cy), fill=BAT_EYE)


def spider(d, cx, y):
    d.line([(cx, 0), (cx, y - 2)], fill=THREAD)
    for dy, dx in [(-3, 4), (-1, 5), (1, 5), (3, 4)]:
        d.line([(cx, y), (cx - dx, y + dy)], fill=SPIDER)
        d.line([(cx, y), (cx + dx, y + dy)], fill=SPIDER)
    disc(d, cx, y, 2, SPIDER)
    d.point((cx - 1, y - 1), fill=BAT_EYE)
    d.point((cx + 1, y - 1), fill=BAT_EYE)


def skeleton(d, cx, top, beat):
    """A dancing skeleton, 26 pixels tall. `beat` (0 or 1) swaps arms and legs."""
    disc(d, cx, top + 4, 4, BONE)
    d.rectangle([cx - 3, top + 3, cx - 2, top + 4], fill=(0, 0, 0))
    d.rectangle([cx + 2, top + 3, cx + 3, top + 4], fill=(0, 0, 0))
    d.point((cx, top + 5), fill=(0, 0, 0))
    for x in range(cx - 2, cx + 3):                                      # teeth
        d.point((x, top + 7), fill=BONE if (x - cx) % 2 == 0 else (0, 0, 0))
    d.line([(cx, top + 9), (cx, top + 17)], fill=BONE)                   # spine
    for dy, half in [(10, 4), (12, 3), (14, 2)]:                         # ribs
        d.line([(cx - half, top + dy), (cx + half, top + dy)], fill=BONE)
    d.rectangle([cx - 2, top + 17, cx + 2, top + 18], fill=BONE)         # pelvis
    up, down = (-5, 3) if beat else (3, -5)
    d.line([(cx - 4, top + 10), (cx - 8, top + 10 + up)], fill=BONE)     # arms
    d.line([(cx + 4, top + 10), (cx + 8, top + 10 + down)], fill=BONE)
    lean = 2 if beat else -2
    d.line([(cx - 2, top + 19), (cx - 3 + lean, top + 25)], fill=BONE)   # legs
    d.line([(cx + 2, top + 19), (cx + 3 + lean, top + 25)], fill=BONE)


def tombstone(d, x, w, h, cross=False):
    top = GROUND_Y - h
    d.rectangle([x, top + 2, x + w - 1, GROUND_Y], fill=TOMB)
    d.line([(x + 1, top), (x + w - 2, top)], fill=TOMB)
    d.line([(x, top + 1), (x + w - 1, top + 1)], fill=TOMB)
    d.line([(x, top + 2), (x, GROUND_Y)], fill=TOMB_HI)
    mid = x + w // 2
    d.line([(mid, top + 3), (mid, top + 7)], fill=TOMB_DARK)
    d.line([(mid - 1, top + 4), (mid + 1, top + 4)], fill=TOMB_DARK)


def eyes(d, x, y, color):
    for dx in (0, 1, 4, 5):
        d.point((x + dx, y), fill=color)
