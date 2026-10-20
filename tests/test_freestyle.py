import pytest
from PIL import Image

from ledwall.screens import FreestyleScreen
from ledwall.screens import freestyle as freestyle_module

RED, BLUE = (255, 0, 0), (0, 0, 255)


def px(screen, x, y):
    return screen.render(0.0).getpixel((x, y))


def test_starts_black_64x64():
    img = FreestyleScreen().render(0.0)
    assert img.size == (64, 64) and img.mode == "RGB"
    assert img.getcolors() == [(4096, (0, 0, 0))]


def test_draw_sets_pixels_and_ignores_out_of_range():
    s = FreestyleScreen()
    s.draw([(3, 4, RED), (63, 63, BLUE), (64, 0, RED), (-1, 5, RED)])
    assert px(s, 3, 4) == RED and px(s, 63, 63) == BLUE
    assert len(s.render(0.0).getcolors()) == 3          # black, red, blue: nothing stray


def test_render_returns_a_copy():
    s = FreestyleScreen()
    s.render(0.0).putpixel((0, 0), RED)
    assert px(s, 0, 0) == (0, 0, 0)


def test_one_stroke_is_one_undo_step():
    s = FreestyleScreen()
    s.draw([(1, 1, RED)], stroke=1)
    s.draw([(2, 2, RED)], stroke=1)                      # same stroke, sent in a second batch
    s.draw([(3, 3, BLUE)], stroke=2)
    assert s.undo() and px(s, 3, 3) == (0, 0, 0) and px(s, 2, 2) == RED
    assert s.undo() and px(s, 1, 1) == (0, 0, 0) and px(s, 2, 2) == (0, 0, 0)
    assert s.undo() is False


def test_calls_without_a_stroke_id_each_undo_separately():
    s = FreestyleScreen()
    s.draw([(1, 1, RED)])
    s.draw([(2, 2, RED)])
    s.undo()
    assert px(s, 1, 1) == RED and px(s, 2, 2) == (0, 0, 0)


def test_flood_fill_fills_the_connected_area_only():
    s = FreestyleScreen()
    s.draw([(10, y, RED) for y in range(64)])             # a wall down column 10
    s.flood(0, 0, BLUE)
    assert px(s, 5, 5) == BLUE and px(s, 10, 5) == RED and px(s, 20, 5) == (0, 0, 0)
    assert s.undo() and px(s, 5, 5) == (0, 0, 0)


def test_flood_fill_with_the_same_color_does_nothing():
    s = FreestyleScreen()
    s.flood(0, 0, (0, 0, 0))
    assert s.undo() is False


def test_clear_and_its_undo():
    s = FreestyleScreen()
    s.draw([(5, 5, RED)])
    s.clear()
    assert px(s, 5, 5) == (0, 0, 0)
    s.undo()
    assert px(s, 5, 5) == RED


def test_undo_history_is_limited():
    s = FreestyleScreen()
    for i in range(freestyle_module.UNDO_LEVELS + 10):
        s.draw([(i % 64, 0, RED)])
    undone = 0
    while s.undo():
        undone += 1
    assert undone == freestyle_module.UNDO_LEVELS


def test_png_is_a_64x64_image():
    import io
    s = FreestyleScreen()
    s.draw([(7, 7, RED)])
    img = Image.open(io.BytesIO(s.png()))
    assert img.size == (64, 64) and img.convert("RGB").getpixel((7, 7)) == RED


def test_sketch_survives_a_restart(tmp_path):
    path = str(tmp_path / "freestyle" / "canvas.png")
    first = FreestyleScreen(path=path)
    first.draw([(9, 9, BLUE)])
    first.save()
    assert px(FreestyleScreen(path=path), 9, 9) == BLUE


def test_unreadable_saved_file_is_ignored(tmp_path):
    bad = tmp_path / "canvas.png"
    bad.write_bytes(b"not a png")
    assert px(FreestyleScreen(path=str(bad)), 0, 0) == (0, 0, 0)
