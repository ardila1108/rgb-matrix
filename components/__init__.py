from PIL import Image
from .image_utils import load_and_scale_image
from .gif_utils import GifPlayer
from .text_utils import ScrollingText, StaticText

def render_component(canvas: Image.Image, component_or_frame, coords: tuple[int, int] = (0, 0)):
    """
    Helper function to cleanly render any component or image onto a canvas.
    Automatically handles fetching the next frame and applying transparency masks.
    """
    # 1. If it's a component class, get the frame. If it's already an Image, just use it.
    frame = component_or_frame.get_next_frame() if hasattr(component_or_frame, 'get_next_frame') else component_or_frame
    
    # 2. Pillow is smart! If the image is RGBA, you can pass the image ITSELF as the mask
    # and Pillow will automatically extract the Alpha channel and use it.
    mask = frame if frame.mode == 'RGBA' else None
    
    # 3. Paste it onto the canvas
    canvas.paste(frame, coords, mask)

__all__ = ["load_and_scale_image", "GifPlayer", "ScrollingText", "StaticText", "render_component"]
