import os
from PIL import Image, ImageDraw

os.makedirs("assets", exist_ok=True)

# 1. Create a simple static image (a smiley face)
img = Image.new("RGB", (32, 32), color=(0, 0, 50))
draw = ImageDraw.Draw(img)
# Face
draw.ellipse([4, 4, 28, 28], fill=(255, 255, 0))
# Eyes
draw.ellipse([10, 10, 14, 14], fill=(0, 0, 0))
draw.ellipse([18, 10, 22, 14], fill=(0, 0, 0))
# Smile
draw.arc([10, 14, 22, 24], start=20, end=160, fill=(0, 0, 0), width=2)
img.save("assets/test_image.png")

# 2. Create a FASTER animated GIF (bouncing ball with fewer frames and larger jumps)
frames = []
# 6 frames instead of 10, jumping by 4 pixels instead of 2
for i in range(6):
    frame = Image.new("RGB", (32, 32), color=(50, 0, 0))
    draw = ImageDraw.Draw(frame)
    y = 4 + (i * 4) if i < 3 else 4 + ((5 - i) * 4)
    draw.ellipse([12, y, 20, y + 8], fill=(0, 255, 0))
    frames.append(frame)

frames[0].save(
    "assets/test_gif.gif",
    save_all=True,
    append_images=frames[1:],
    duration=50,  # Note: our GifPlayer ignores this native duration, but it's good practice
    loop=0
)
