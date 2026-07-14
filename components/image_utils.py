from PIL import Image

def load_and_scale_image(filepath: str, width: int = 64, height: int = 64) -> Image.Image:
    """
    Loads an image from the filepath and scales it to fit the matrix dimensions.
    Returns a PIL Image.
    """
    try:
        img = Image.open(filepath).convert("RGB")
        # Resize to fit exactly (you can change this to Image.Resampling.NEAREST for pixel art)
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"Error loading image {filepath}: {e}")
        # Return a blank image on failure
        return Image.new("RGB", (width, height))
