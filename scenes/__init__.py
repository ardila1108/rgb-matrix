"""
Scene registry.

To add a new scene:
  1. Create a new file in this folder, e.g. scenes/my_scene.py
  2. Define a render function: def render_my_scene() -> Image.Image
  3. Import it here and add it to SCENES with a key name.

That key name is what the API and UI buttons will use.
"""
from scenes.hello_world import render_hello_world
from scenes.heart import render_heart
from scenes.clock import render_clock
from scenes.components_test import render_components_test

SCENES: dict = {
    "hello_world": render_hello_world,
    "heart": render_heart,
    "clock": render_clock,
    "components_test": render_components_test,
}
