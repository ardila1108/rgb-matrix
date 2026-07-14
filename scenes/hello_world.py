from PIL import Image, ImageDraw


def render_hello_world() -> Image.Image:
    image = Image.new("RGB", (64, 64))
    draw = ImageDraw.Draw(image)
    draw.text((12, 12), "Hello", fill=(255, 0, 0))   # Red
    draw.text((12, 36), "World", fill=(0, 255, 255))  # Cyan
    return image
