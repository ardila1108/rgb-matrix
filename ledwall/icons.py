"""Little pixel-art helpers: sun, moon (with phase), clouds, rain, snow, bolt."""
import math

BLACK = (0, 0, 0)
SUN = (255, 200, 0)
SUN_RAY = (255, 150, 0)
MOON_LIT = (230, 230, 210)
MOON_DARK = (35, 35, 50)
CLOUD_LIGHT = (185, 195, 205)
CLOUD_GRAY = (150, 160, 175)
CLOUD_DARK = (105, 115, 130)
CLOUD_STORM = (80, 88, 105)
DROP = (60, 140, 255)
SNOW = (235, 240, 255)
BOLT = (255, 225, 60)
FOG = (140, 150, 165)
STAR = (200, 200, 255)


def disc(d, cx, cy, r, color):
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            if x * x + y * y <= r * r + 0.5:
                d.point((cx + x, cy + y), fill=color)


def sun(d, cx, cy, r, tick):
    """A disc with eight rays that flicker between two lengths."""
    disc(d, cx, cy, r, SUN)
    for k in range(8):
        angle = k * math.pi / 4
        length = 2 if (tick % 2 == 0 or k % 2 == 0) else 1
        for dist in range(r + 2, r + 2 + length):
            d.point((round(cx + math.cos(angle) * dist), round(cy + math.sin(angle) * dist)), fill=SUN_RAY)


def moon(d, cx, cy, r, phase, lit=MOON_LIT, dark=MOON_DARK):
    """A moon disc showing `phase` (0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter).

    Waxing phases are lit from the right (northern hemisphere), waning from the left.
    """
    r2 = (r + 0.3) ** 2
    k = math.cos(2 * math.pi * phase)
    for y in range(-r, r + 1):
        w = math.sqrt(max(0.0, r2 - y * y))
        for x in range(-r, r + 1):
            if x * x + y * y > r2:
                continue
            lit_here = x > w * k if phase <= 0.5 else x < -w * k
            d.point((cx + x, cy + y), fill=lit if lit_here else dark)


def cloud(d, cx, cy, color):
    disc(d, cx - 5, cy + 2, 4, color)
    disc(d, cx, cy, 5, color)
    disc(d, cx + 5, cy + 2, 4, color)
    for y in range(cy + 2, cy + 7):
        for x in range(cx - 9, cx + 10):
            d.point((x, y), fill=color)


def rain(d, cx, cy, tick):
    for i in range(4):
        x, y = cx - 7 + i * 4, cy + 9 + (tick + i * 2) % 5
        d.point((x, y), fill=DROP)
        d.point((x - 1, y + 1), fill=DROP)


def snow(d, cx, cy, tick):
    for i in range(4):
        x, y = cx - 7 + i * 4 + (1 if (tick + i) % 2 else 0), cy + 9 + (tick + i * 2) % 5
        d.point((x, y), fill=SNOW)


def fog(d, cx, cy):
    for i in range(3):
        for x in range(cx - 8 + i, cx + 8 - i):
            d.point((x, cy + 9 + i * 3), fill=FOG)


def bolt(d, cx, cy):
    for (x, y) in [(2, 0), (1, 1), (0, 2), (1, 2), (2, 2), (1, 3), (0, 4), (0, 5), (-1, 6)]:
        d.point((cx + x, cy + y), fill=BOLT)
        d.point((cx + x + 1, cy + y), fill=BOLT)


def stars(d, tick, points):
    for i, (x, y) in enumerate(points):
        if (tick + i) % 3 != 0:
            d.point((x, y), fill=STAR)
