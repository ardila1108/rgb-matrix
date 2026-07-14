from PIL import Image, ImageDraw


def render_heart() -> Image.Image:
    image = Image.new("RGB", (64, 64))
    draw = ImageDraw.Draw(image)

    heart_color = (220, 20, 60)  # Crimson red
    cx, cy = 32, 30              # Centre point
    r = 8

    # Two circles form the upper bumps of the heart
    draw.ellipse([cx - r - r + 2, cy - r, cx - 2, cy + r - 2], fill=heart_color)
    draw.ellipse([cx + 2, cy - r, cx + r + r - 2, cy + r - 2], fill=heart_color)

    # Triangle forms the lower point of the heart
    draw.polygon(
        [
            (cx - r - r + 2, cy + 4),
            (cx + r + r - 2, cy + 4),
            (cx, cy + r + r - 2),
        ],
        fill=heart_color,
    )
    return image
