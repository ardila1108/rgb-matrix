import pytest

import settings
from ledwall import font, halloween_art as art
from ledwall.automation import build_schedule
from ledwall.screens import HalloweenScreen
from tests.test_automation import KNOWN

ACT = settings.HALLOWEEN_ACT_SECONDS


def at(screen, act, t, start=100.0):
    """Render the given act at t seconds into it."""
    screen._act, screen._act_start, screen._last = act, start, start + t - 0.05
    return screen.render(start + t)


def play(screen, seconds, step=0.1, start=0.0):
    """Render continuously like the main loop; returns [(time, act), ...]."""
    out, t = [], start
    while t <= start + seconds + 1e-9:
        screen.render(t)
        out.append((round(t, 2), screen.act))
        t += step
    return out


def act_at(played, t):
    return next(act for time, act in played if abs(time - t) < 1e-6)


def count(img, color=None, box=(0, 0, 64, 64)):
    x0, y0, x1, y1 = box
    pixels = [img.getpixel((x, y)) for x in range(x0, x1) for y in range(y0, y1)]
    return sum(1 for p in pixels if (p == color if color else p != art.sky().getpixel((0, 0)))), len(pixels)


def test_frame_is_64x64_rgb_and_not_empty():
    img = HalloweenScreen().render(0.0)
    assert img.size == (64, 64) and img.mode == "RGB"
    assert len(img.getcolors(5000)) > 5


@pytest.mark.parametrize("act", range(4))
@pytest.mark.parametrize("t", [0.0, 0.5, 1.7, 3.3, 5.0, 7.2, 8.4, 9.9])
def test_every_act_renders_at_every_moment(act, t):
    img = at(HalloweenScreen(), act, t)
    assert img.size == (64, 64)


def test_the_screen_is_a_normal_menu_screen():
    s = HalloweenScreen()
    assert s.name == "halloween" and s.label == "Halloween" and s.fps == 10
    s.update({"anything": 1})                                   # accepts and ignores data


# ---- the acts follow each other ------------------------------------------------------------
def test_acts_follow_one_another_every_act_length():
    played = play(HalloweenScreen(), 4 * ACT + 1)
    expected = [(0.0, 0), (ACT - 0.5, 0), (ACT + 0.5, 1), (2 * ACT + 0.5, 2), (3 * ACT + 0.5, 3), (4 * ACT + 0.5, 0)]
    for t, act in expected:
        assert act_at(played, round(t, 2)) == act, t


def test_coming_back_after_being_away_starts_the_next_act():
    s = HalloweenScreen()
    s.render(0.0)
    s.render(0.1)
    assert s.act == 0
    s.render(200.0)                                             # the rotation went elsewhere for a while
    assert s.act == 1
    s.render(200.1)
    assert s.act == 1                                           # it keeps playing while on screen
    s.render(500.0)
    assert s.act == 2


def test_an_act_always_starts_from_its_beginning():
    s = HalloweenScreen()
    s.render(0.0)
    first = s.render(300.0)                                     # next act, t = 0
    again = HalloweenScreen()
    again._act, again._act_start, again._last = 1, 300.0, 299.95
    assert first.tobytes() == again.render(300.0).tobytes()


def test_act_length_is_a_setting_and_has_a_floor(monkeypatch):
    monkeypatch.setattr(settings, "HALLOWEEN_ACT_SECONDS", 4)
    played = play(HalloweenScreen(), 9)
    assert act_at(played, 3.9) == 0 and act_at(played, 4.2) == 1 and act_at(played, 8.3) == 2
    monkeypatch.setattr(settings, "HALLOWEEN_ACT_SECONDS", 0.2)     # silly value: floor of 3 seconds
    played = play(HalloweenScreen(), 4)
    assert act_at(played, 2.9) == 0 and act_at(played, 3.2) == 1


# ---- things really appear over time ----------------------------------------------------------
def test_title_letters_appear_one_at_a_time():
    box = (3, 4, 61, 18)
    early = count(at(HalloweenScreen(), 0, 0.1), art.GLOW, box)[0] + count(at(HalloweenScreen(), 0, 0.1), art.GLOW_D, box)[0]
    late = count(at(HalloweenScreen(), 0, 2.0), art.GLOW, box)[0] + count(at(HalloweenScreen(), 0, 2.0), art.GLOW_D, box)[0]
    assert 0 < early < late
    assert count(at(HalloweenScreen(), 0, 1.0), art.PURPLE_TEXT, (5, 23, 59, 30))[0] == 0     # HALLOWEEN not yet
    assert count(at(HalloweenScreen(), 0, 4.0), art.PURPLE_TEXT, (5, 23, 59, 30))[0] > 30


def test_pumpkins_pop_up_one_after_the_other():
    orange = lambda t: count(at(HalloweenScreen(), 1, t), art.ORANGE)[0]
    assert orange(0.3) == 0                                     # nothing yet
    assert 0 < orange(1.0) < orange(2.0) < orange(3.5)


def test_the_pumpkin_candle_flickers():
    s = HalloweenScreen()
    glows = {tuple(sorted(c for _, c in at(s, 1, 4.0 + i * 0.25).getcolors(5000)
                          if c in (art.GLOW, art.GLOW_D))) for i in range(8)}
    assert len(glows) >= 1
    frames = {at(HalloweenScreen(), 1, 4.0 + i * 0.25).tobytes() for i in range(8)}
    assert len(frames) > 1                                      # it is never a frozen picture


def test_a_ghost_fades_in_and_out_while_crossing():
    def ghost_pixels(t):
        img = at(HalloweenScreen(), 1, t)
        pixels = (img.getpixel((x, y)) for x in range(64) for y in range(10, 36))
        return sum(1 for r, g, b in pixels if r > 150 and b > 180)       # ghost white, not moon or eyes
    stars = 4                                                    # a few stars can sit in the same area
    assert ghost_pixels(1.4) <= stars                            # not there yet
    assert ghost_pixels(5.0) > 40                                # in the middle: clearly visible
    assert ghost_pixels(9.5) <= stars                            # gone again


def test_the_skeleton_rises_out_of_the_ground_and_dances():
    def bone(t):
        return count(at(HalloweenScreen(), 2, t), art.BONE, (22, 20, 50, 58))[0]
    assert bone(0.2) == 0
    assert bone(0.2) < bone(1.2) < bone(2.5)
    beat_a, beat_b = at(HalloweenScreen(), 2, 4.0), at(HalloweenScreen(), 2, 4.4)
    assert beat_a.tobytes() != beat_b.tobytes()                 # arms and legs swap each beat


def test_boo_appears_only_near_the_end_of_the_moon_act():
    red = lambda t: count(at(HalloweenScreen(), 3, t), art.RED, (5, 34, 60, 52))[0]
    assert red(3.0) == 0 and red(6.0) == 0
    assert max(red(7.0), red(7.25), red(7.5)) > 20
    assert red(9.8) == 0


def test_the_spider_goes_up_and_down_its_thread():
    def spider_rows(t):
        img = at(HalloweenScreen(), 3, t)
        return max((y for y in range(0, 40) for x in range(6, 19) if img.getpixel((x, y)) == art.SPIDER), default=-1)
    low, high = spider_rows(3.5), spider_rows(0.1)
    assert low > high


def test_nothing_is_drawn_below_the_ground_line_except_the_ground():
    img = at(HalloweenScreen(), 2, 0.1)                         # skeleton is still underground
    for x in range(64):
        for y in range(art.GROUND_Y + 1, 64):
            assert img.getpixel((x, y)) == art.GROUND


# ---- helpers ------------------------------------------------------------------------------
def test_exclamation_mark_exists_in_the_font():
    assert font.glyph("!") != font.glyph(" ")


def test_scale_and_clamp():
    assert art.scale((200, 100, 50), 0.5) == (100, 50, 25)
    assert art.scale((200, 100, 50), 2) == (200, 100, 50) and art.scale((200, 100, 50), -1) == (0, 0, 0)
    assert art.clamp(5) == 1 and art.clamp(-5) == 0 and art.clamp(0.3) == 0.3


def test_pumpkin_below_the_pop_threshold_draws_nothing():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (64, 64))
    art.pumpkin(ImageDraw.Draw(img), 32, 32, grow=0.0)
    assert img.getcolors() == [(4096, (0, 0, 0))]


# ---- in the schedule ------------------------------------------------------------------------
def test_halloween_is_in_the_default_rotation_and_the_menu():
    assert "halloween" in settings.DEFAULT_SCREENS and "halloween" in settings.MENU_SCREENS
    build_schedule(KNOWN)                                       # the shipped schedule is valid


def test_it_can_be_given_its_own_time_in_a_rotation():
    from types import SimpleNamespace
    cfg = SimpleNamespace(ROTATION_SECONDS=20, DEFAULT_SCREENS=("clock", "weather", ("halloween", 40)),
                          SCREEN_SCHEDULE=[], BRIGHTNESS_SCHEDULE=[], BRIGHTNESS=80)
    sched = build_schedule(KNOWN, cfg)
    from tests.test_automation import at as moment
    assert sched.plan_at(moment(12)) == (("clock", 20.0), ("weather", 20.0), ("halloween", 40.0))
