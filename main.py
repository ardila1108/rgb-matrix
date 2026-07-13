import os
import io
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from PIL import Image
from dotenv import load_dotenv

from scenes import SCENES
from ui import render_ui

load_dotenv()

MATRIX_ENV = os.getenv("MATRIX_ENV", "virtual").lower()

# ── State ──────────────────────────────────────────────────────────────────────
current_scene: str = "hello_world"
matrix = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_current_frame() -> Image.Image:
    """Return a rendered PIL image for the current scene."""
    render_fn = SCENES.get(current_scene, SCENES["hello_world"])
    return render_fn()


def image_to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global matrix

    if MATRIX_ENV == "physical":
        try:
            from rgbmatrix import RGBMatrix, RGBMatrixOptions
            print("Initializing physical RGB Matrix...")
            options = RGBMatrixOptions()
            options.rows = 64
            options.cols = 64
            options.chain_length = 1
            options.parallel = 1
            options.disable_hardware_pulsing = True
            options.hardware_mapping = "regular"
            options.brightness = 80
            matrix = RGBMatrix(options=options)

            async def matrix_update_loop():
                while True:
                    matrix.SetImage(get_current_frame())
                    await asyncio.sleep(0.1)  # ~10 fps

            asyncio.create_task(matrix_update_loop())
            print("Matrix background loop started.")
        except ImportError:
            print("WARNING: rgbmatrix library not found. Physical mode unavailable.")

    yield  # ← server runs here

    if matrix:
        matrix.Clear()
        print("Matrix cleared.")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="RGB Matrix Controller", lifespan=lifespan)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=render_ui(MATRIX_ENV, current_scene, list(SCENES.keys())))


@app.post("/set-scene/{scene_name}")
async def set_scene(scene_name: str):
    global current_scene
    if scene_name not in SCENES:
        return {"error": f"Unknown scene '{scene_name}'. Available: {list(SCENES.keys())}"}
    current_scene = scene_name
    return {"active_scene": current_scene}


@app.get("/matrix-image")
async def get_matrix_image():
    """Returns the current frame as a PNG (used by the virtual preview)."""
    return Response(content=image_to_png_bytes(get_current_frame()), media_type="image/png")


@app.get("/state")
async def get_state():
    return {
        "matrix_env": MATRIX_ENV,
        "current_scene": current_scene,
        "available_scenes": list(SCENES.keys()),
    }
