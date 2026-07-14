from PIL import Image, ImageDraw, ImageFont

class ScrollingText:
    """
    A helper class to create scrolling text that animates across the matrix.
    Instantiate this at the top level of your scene file so its state persists.
    """
    def __init__(self, text: str, color: tuple = (255, 255, 255), y_pos: int = 20, width: int = 64, height: int = 64, speed: int = 2, bg_color: tuple = None):
        self.text = text
        self.color = color
        self.bg_color = bg_color
        self.y_pos = y_pos
        self.width = width
        self.height = height
        self.speed = speed
        self.x_pos = width # Start off-screen to the right
        
        # Load default font
        try:
            # You can place a specific .ttf file in an assets folder if you want custom fonts
            self.font = ImageFont.truetype("arial.ttf", 16)
        except IOError:
            self.font = ImageFont.load_default()
            
        # Calculate text width
        dummy_img = Image.new("RGB", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        
        # getbbox returns (left, top, right, bottom)
        try:
            bbox = dummy_draw.textbbox((0, 0), self.text, font=self.font)
            self.text_width = bbox[2] - bbox[0]
        except AttributeError:
            # Fallback for older PIL versions
            self.text_width, _ = dummy_draw.textsize(self.text, font=self.font)

    def get_next_frame(self) -> Image.Image:
        """Draws the text at the current position, advances it, and returns the frame."""
        bg = self.bg_color + (255,) if self.bg_color else (0, 0, 0, 0)
        image = Image.new("RGBA", (self.width, self.height), bg)
        draw = ImageDraw.Draw(image)
        
        draw.text((self.x_pos, self.y_pos), self.text, font=self.font, fill=self.color)
        
        self.x_pos -= self.speed
        if self.x_pos + self.text_width < 0:
            self.x_pos = self.width # Reset to start once it scrolls off-screen
            
        return image

class StaticText:
    """
    A helper class to create static text that stays in place.
    Instantiate this at the top level of your scene file so its state persists.
    """
    def __init__(self, text: str, color: tuple = (255, 255, 255), x_pos: int = 0, y_pos: int = 20, width: int = 64, height: int = 64, bg_color: tuple = None):
        self.text = text
        self.color = color
        self.bg_color = bg_color
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.width = width
        self.height = height
        
        # Load default font
        try:
            self.font = ImageFont.truetype("arial.ttf", 16)
        except IOError:
            self.font = ImageFont.load_default()

    def get_next_frame(self) -> Image.Image:
        """Draws the text at the fixed position and returns the frame."""
        bg = self.bg_color + (255,) if self.bg_color else (0, 0, 0, 0)
        image = Image.new("RGBA", (self.width, self.height), bg)
        draw = ImageDraw.Draw(image)
        
        draw.text((self.x_pos, self.y_pos), self.text, font=self.font, fill=self.color)
        return image
