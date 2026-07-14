from PIL import Image, ImageDraw
from datetime import datetime


def render_clock() -> Image.Image:
    image = Image.new("RGB", (64, 64))
    draw = ImageDraw.Draw(image)

    now = datetime.now()
    seconds = now.second

    # ── Time strings ──────────────────────────────────────────────────────────
    hour_str = now.strftime("%H")
    min_str  = now.strftime("%M")
    sec_str  = now.strftime("%S")

    # Blinking colon: visible on even seconds, dim on odd seconds
    colon_color = (0, 200, 255) if seconds % 2 == 0 else (0, 60, 80)

    # ── Draw HH : MM centred on the top half ─────────────────────────────────
    # Default PIL font is 6px wide × 8px tall per character
    # "HH:MM" = 5 chars × 6 = 30px wide → start at x=17 to centre in 64px
    time_color = (0, 200, 255)   # Cyan
    draw.text((17,  14), hour_str,  fill=time_color)
    draw.text((29,  14), ":",       fill=colon_color)
    draw.text((35,  14), min_str,   fill=time_color)

    # ── Seconds label ─────────────────────────────────────────────────────────
    # "SS" = 2 chars × 6 = 12px → centre at x=26
    sec_color = (120, 120, 140)
    draw.text((26, 26), sec_str, fill=sec_color)

    # ── Seconds progress bar ──────────────────────────────────────────────────
    # A thin bar at the bottom that fills left-to-right over 60 seconds.
    # It glows brighter as it nears the minute.
    BAR_TOP, BAR_BOT = 38, 44
    BAR_LEFT, BAR_RIGHT = 2, 61

    # Background track
    draw.rectangle([BAR_LEFT, BAR_TOP, BAR_RIGHT, BAR_BOT], fill=(20, 30, 40))

    # Filled portion — colour shifts from blue → cyan → white as seconds advance
    progress = seconds / 59
    fill_right = BAR_LEFT + int(progress * (BAR_RIGHT - BAR_LEFT))
    r = int(progress * 255)
    g = int(200 + progress * 55)
    b = 255
    draw.rectangle([BAR_LEFT, BAR_TOP, fill_right, BAR_BOT], fill=(r, g, b))

    # ── Day-of-week label ─────────────────────────────────────────────────────
    day_str = now.strftime("%a").upper()   # MON, TUE, …
    # 3 chars × 6 = 18px → centre at x=23
    draw.text((23, 50), day_str, fill=(80, 80, 100))

    return image
