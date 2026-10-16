import pytest

import settings
from ledwall.screens import TestScreen

STEP = settings.TEST_SECONDS_PER_PATTERN


@pytest.mark.parametrize("i", range(4))
def test_every_pattern_renders_64x64(i):
    img = TestScreen().render(i * STEP + 0.1)
    assert img.size == (64, 64) and img.mode == "RGB"


def test_grid_corners_and_bars():
    s = TestScreen()
    bars = s.render(0.1)
    assert bars.getpixel((2, 2)) == (255, 255, 255)
    grid = s.render(STEP + 0.1)
    assert grid.getpixel((2, 2)) == (255, 0, 0)
    assert grid.getpixel((62, 2)) == (0, 255, 0)
    assert grid.getpixel((2, 62)) == (0, 0, 255)


def test_fill_cycles_colors():
    s = TestScreen()
    t = 3 * STEP
    assert len({s.render(t + k).getpixel((5, 5)) for k in range(4)}) == 4
