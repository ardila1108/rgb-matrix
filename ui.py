"""
UI renderer.

Generates the HTML string for the web controller page.
Called by the GET / endpoint in main.py.
"""

# Human-readable labels and emoji for each scene key.
# If a scene is not listed here it will fall back to a capitalised key name.
SCENE_LABELS: dict[str, str] = {
    "hello_world": "💬 Hello World",
    "heart": "❤️ Heart",
    "clock": "🕐 Clock",
}


def render_ui(matrix_env: str, current_scene: str, available_scenes: list[str]) -> str:
    """Return the full HTML string for the controller page."""

    preview_block = _preview_block() if matrix_env == "virtual" else ""
    preview_script = _preview_script() if matrix_env == "virtual" else ""
    buttons_html = _buttons_html(available_scenes)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>RGB Matrix Controller</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            background-color: #1a1a2e;
            color: #e0e0e0;
            font-family: 'Segoe UI', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
            gap: 32px;
        }}

        h1 {{
            font-size: 1.8rem;
            letter-spacing: 2px;
            color: #a0c4ff;
        }}

        .badge {{
            background: #0f3460;
            color: #a0c4ff;
            padding: 4px 14px;
            border-radius: 999px;
            font-size: 0.8rem;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            justify-content: center;
        }}

        .scene-btn {{
            padding: 14px 28px;
            border: 2px solid #334;
            border-radius: 12px;
            background: #16213e;
            color: #ccc;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
            letter-spacing: 0.5px;
        }}

        .scene-btn:hover {{
            border-color: #a0c4ff;
            color: #fff;
            background: #0f3460;
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(160, 196, 255, 0.2);
        }}

        .scene-btn.active {{
            border-color: #a0c4ff;
            background: #0f3460;
            color: #fff;
            box-shadow: 0 0 12px rgba(160, 196, 255, 0.4);
        }}

        .preview-section {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }}

        .preview-section h2 {{
            font-size: 1rem;
            color: #778;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .matrix-container {{
            border: 3px solid #0f3460;
            padding: 8px;
            background: #000;
            border-radius: 8px;
            box-shadow: 0 0 30px rgba(0, 120, 255, 0.15);
        }}

        #matrix-img {{
            width: 384px;
            height: 384px;
            image-rendering: pixelated;
            display: block;
        }}

        .feedback {{
            font-size: 0.85rem;
            color: #556;
            height: 20px;
            transition: color 0.3s;
        }}
        .feedback.ok  {{ color: #7ecb7e; }}
        .feedback.err {{ color: #e07070; }}
    </style>
</head>
<body>
    <h1>RGB Matrix Controller</h1>
    <span class="badge">Mode: {matrix_env}</span>

    <div class="controls">
        {buttons_html}
    </div>

    <div class="feedback" id="feedback"></div>

    {preview_block}

    <script>
        let activeScene = "{current_scene}";

        async function setScene(name) {{
            const feedback = document.getElementById('feedback');
            try {{
                const res = await fetch('/set-scene/' + name, {{ method: 'POST' }});
                const data = await res.json();
                if (data.active_scene) {{
                    activeScene = data.active_scene;
                    updateActiveButton();
                    feedback.textContent = 'Scene set to: ' + data.active_scene;
                    feedback.className = 'feedback ok';
                }} else {{
                    feedback.textContent = data.error || 'Unknown error';
                    feedback.className = 'feedback err';
                }}
            }} catch (e) {{
                feedback.textContent = 'Request failed: ' + e.message;
                feedback.className = 'feedback err';
            }}
            setTimeout(() => {{
                feedback.textContent = '';
                feedback.className = 'feedback';
            }}, 2500);
        }}

        function updateActiveButton() {{
            document.querySelectorAll('.scene-btn').forEach(btn => btn.classList.remove('active'));
            const active = document.getElementById('btn-' + activeScene);
            if (active) active.classList.add('active');
        }}

        // Highlight the current scene on page load
        updateActiveButton();

        {preview_script}
    </script>
</body>
</html>"""


# ── Private helpers ────────────────────────────────────────────────────────────

def _buttons_html(available_scenes: list[str]) -> str:
    buttons = []
    for scene_key in available_scenes:
        label = SCENE_LABELS.get(scene_key, scene_key.replace("_", " ").title())
        buttons.append(
            f'<button class="scene-btn" id="btn-{scene_key}" onclick="setScene(\'{scene_key}\')">'
            f"{label}"
            f"</button>"
        )
    return "\n        ".join(buttons)


def _preview_block() -> str:
    return """
        <div class="preview-section">
            <h2>Matrix Preview</h2>
            <div class="matrix-container">
                <img id="matrix-img" src="/matrix-image" alt="Matrix Preview" />
            </div>
        </div>"""


def _preview_script() -> str:
    return """
        setInterval(() => {
            const img = document.getElementById('matrix-img');
            if (img) img.src = '/matrix-image?t=' + new Date().getTime();
        }, 500);"""
