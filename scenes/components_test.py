import os
from PIL import Image

from components import ScrollingText, StaticText, GifPlayer, load_and_scale_image, render_component

# 1. Initialize our components at the module level so they hold state across frames
text_scroller = ScrollingText(text="TESTING!", color=(255, 255, 0), y_pos=2, width=64, height=16, speed=1)

# Creates scrolling text with a solid blue background behind it
text_scroller = ScrollingText(
    text="WARNING!", 
    color=(255, 255, 255),
    y_pos=2, width=64, height=16,
    bg_color=(0, 0, 255)  # The block behind the text will be solid blue
)

# Add a StaticText component to demonstrate it
static_text = StaticText(text="STAY", color=(255, 100, 255), x_pos=16, y_pos=0, width=64, height=16)

# Ensure assets exist before loading
gif_path = "assets/pepsi_logo.gif"
img_path = "assets/test_image.png"

# Load the GIF player. We scale it to 32x32 so it takes up exactly a quadrant
gif_player = GifPlayer(gif_path, width=64, height=64)

# Load the static image. We scale it to 32x32 as well
static_image = load_and_scale_image(img_path, width=32, height=32)

def render_components_test() -> Image.Image:
    """
    Composites the scrolling text, static text, animated GIF, and static image 
    onto a single 64x64 canvas.
    """
    canvas = Image.new("RGB", (64, 64), color=(0, 0, 0))
    
    # Render all components cleanly using our new helper!
    render_component(canvas, text_scroller, (0, 0))
    #render_component(canvas, static_text, (0, 16))
    #render_component(canvas, gif_player, (0, 0))
    #render_component(canvas, static_image, (32, 32))
    
    return canvas
