"""Where finished frames go: the real panel or a browser preview."""
import io
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image, ImageChops, ImageDraw

import settings

log = logging.getLogger(__name__)


class HardwareBackend:
    """Real panel through hzeller's rpi-rgb-led-matrix (Pi only)."""

    def __init__(self):
        from rgbmatrix import RGBMatrix, RGBMatrixOptions   # only exists on the Pi image

        o = RGBMatrixOptions()
        o.rows = settings.ROWS
        o.cols = settings.COLS
        o.chain_length = 1
        o.parallel = 1
        o.hardware_mapping = settings.HARDWARE_MAPPING
        o.disable_hardware_pulsing = settings.DISABLE_HARDWARE_PULSING
        o.brightness = settings.BRIGHTNESS
        if settings.GPIO_SLOWDOWN is not None:
            o.gpio_slowdown = settings.GPIO_SLOWDOWN
        for attr, value in (("pwm_bits", settings.PWM_BITS),
                            ("limit_refresh_rate_hz", settings.LIMIT_REFRESH_HZ),
                            ("pwm_lsb_nanoseconds", settings.PWM_LSB_NANOSECONDS)):
            if value is not None:
                setattr(o, attr, value)
        o.drop_privileges = False   # we run as root inside the container
        log.info("matrix: %dx%d mapping=%s pulsing_disabled=%s slowdown=%s brightness=%s "
                 "pwm_bits=%s refresh_limit=%s lsb_ns=%s fps=%s",
                 o.rows, o.cols, o.hardware_mapping, o.disable_hardware_pulsing,
                 settings.GPIO_SLOWDOWN, o.brightness, settings.PWM_BITS,
                 settings.LIMIT_REFRESH_HZ, settings.PWM_LSB_NANOSECONDS, settings.FPS)
        self._matrix = RGBMatrix(options=o)
        self._canvas = self._matrix.CreateFrameCanvas()
        self.brightness = settings.BRIGHTNESS

    def set_brightness(self, percent):
        """Change brightness while running (1-100)."""
        percent = max(1, min(100, int(percent)))
        self._matrix.brightness = percent
        self._canvas.brightness = percent
        self.brightness = percent

    def show(self, image):
        self._canvas.SetImage(image.convert("RGB"))
        self._canvas = self._matrix.SwapOnVSync(self._canvas)

    def close(self):
        self._matrix.Clear()


_PAGE = b"""<!doctype html><meta charset=utf-8><title>LED wall</title>
<body style="margin:0;background:#000;display:flex;min-height:100vh;align-items:center;justify-content:center">
<img id=f style="width:min(90vmin,640px);image-rendering:pixelated">
<script>const f=document.getElementById('f');
setInterval(()=>{f.src='/frame.png?'+Date.now()},100)</script>"""


class SimulatorBackend:
    """Serves the latest frame as an LED-looking PNG at http://localhost:PORT."""

    SCALE = 8

    def __init__(self, port=None):
        self._png = b""
        self._lock = threading.Lock()
        self.brightness = settings.BRIGHTNESS
        s = self.SCALE
        size = (settings.COLS * s, settings.ROWS * s)
        self._lit = Image.new("RGB", size, (0, 0, 0))     # multiply mask: dot shape
        self._off = Image.new("RGB", size, (0, 0, 0))     # faint unlit LEDs
        dl, do = ImageDraw.Draw(self._lit), ImageDraw.Draw(self._off)
        for y in range(settings.ROWS):
            for x in range(settings.COLS):
                box = [x * s + 1, y * s + 1, x * s + s - 2, y * s + s - 2]
                dl.ellipse(box, fill=(255, 255, 255))
                do.ellipse(box, fill=(18, 18, 18))

        backend = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith("/frame.png"):
                    with backend._lock:
                        body, kind = backend._png, "image/png"
                else:
                    body, kind = _PAGE, "text/html"
                self.send_response(200)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("0.0.0.0", settings.SIMULATOR_PORT if port is None else port), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    @property
    def port(self):
        return self._server.server_address[1]

    def set_brightness(self, percent):
        """The preview dims like the real panel does."""
        self.brightness = max(1, min(100, int(percent)))

    def show(self, image):
        big = image.convert("RGB").resize(self._lit.size, Image.NEAREST)
        factor = self.brightness / 100
        big = big.point(lambda v: int(v * factor))
        out = ImageChops.lighter(ImageChops.multiply(big, self._lit), self._off)
        buf = io.BytesIO()
        out.save(buf, "PNG")
        with self._lock:
            self._png = buf.getvalue()

    def close(self):
        self._server.shutdown()


def make_backend():
    if settings.BACKEND == "hardware":
        return HardwareBackend()
    if settings.BACKEND == "simulator":
        return SimulatorBackend()
    raise ValueError(f"unknown BACKEND: {settings.BACKEND!r}")
