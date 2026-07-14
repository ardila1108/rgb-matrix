from PIL import Image

class GifPlayer:
    """
    A helper class to load a GIF and return its frames sequentially.
    Instantiate this at the top level of your scene file so its state persists.
    """
    def __init__(self, filepath: str, width: int = 64, height: int = 64, speed: float = 1.0):
        self.width = width
        self.height = height
        self.speed = speed
        self.frames = []
        self.current_frame = 0.0
        self.load_gif(filepath)

    def load_gif(self, filepath: str):
        try:
            gif = Image.open(filepath)
            for frame_idx in range(gif.n_frames):
                gif.seek(frame_idx)
                
                # Convert frame to RGBA first to correctly process transparent palette colors
                rgba_frame = gif.convert("RGBA")
                
                # Create a solid black RGB background (unlit LEDs)
                bg = Image.new("RGB", rgba_frame.size, (0, 0, 0))
                
                # Paste the RGBA frame onto the black background using its own alpha as a mask
                bg.paste(rgba_frame, (0, 0), rgba_frame)
                
                # Resize the cleaned-up RGB frame to the matrix dimensions
                final_frame = bg.resize((self.width, self.height), Image.Resampling.LANCZOS)
                
                self.frames.append(final_frame)
        except Exception as e:
            print(f"Error loading GIF {filepath}: {e}")
            self.frames.append(Image.new("RGB", (self.width, self.height)))

    def get_next_frame(self) -> Image.Image:
        """Returns the next frame in the GIF animation sequence."""
        if not self.frames:
            return Image.new("RGB", (self.width, self.height))
        
        # We cast current_frame to int so it can be a float internally (e.g. speed=1.5)
        frame_index = int(self.current_frame) % len(self.frames)
        frame = self.frames[frame_index]
        
        self.current_frame = (self.current_frame + self.speed) % len(self.frames)
        return frame
