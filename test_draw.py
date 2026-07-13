import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw

# Configure Matrix Options
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.disable_hardware_pulsing = True
options.hardware_mapping = 'regular'
options.brightness = 80  # You have a 10A supply, so you can make it nice and bright!

# Initialize the matrix
matrix = RGBMatrix(options = options)

# Create a blank 64x64 canvas
image = Image.new("RGB", (64, 64))
draw = ImageDraw.Draw(image)

# Draw your multicolored text (X, Y coordinates)
draw.text((12, 12), "Hello", fill=(255, 0, 0))    # Vibrant Red
draw.text((12, 36), "World", fill=(0, 255, 255))  # Vibrant Cyan

# Push to the matrix
matrix.SetImage(image)

try:
    print("Press CTRL+C to stop.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    matrix.Clear()