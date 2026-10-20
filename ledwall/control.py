"""Phone control page: switch screens from a browser on your home network.

GET  /             the page
GET  /api/state    {"active": "bus", "screens": [{"name", "label", "icon", "page"?}, ...]}
POST /api/screen   {"name": "clock"}  -> same JSON as /api/state

Sketching (screen "freestyle"):
GET  /draw                  the sketch page
GET  /api/draw/canvas.png   the current 64x64 canvas
POST /api/draw              {"stroke": 7, "pixels": [[x, y, "#rrggbb"], ...]}
POST /api/draw/fill         {"x": 3, "y": 4, "color": "#rrggbb"}
POST /api/draw/clear        {}
POST /api/draw/undo         {}
No login: keep this port on your home network only.
"""
import json
import logging
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .draw_page import DRAW_PAGE

log = logging.getLogger(__name__)

MAX_BODY_BYTES = 128 * 1024
MAX_PIXELS_PER_REQUEST = 4096
GRID = 64
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class BadRequest(Exception):
    pass


def parse_color(value):
    if not isinstance(value, str) or not _HEX.match(value):
        raise BadRequest(f"color must look like #ff8800, got {value!r}")
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def parse_cell(x, y):
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (x, y)) \
            or not (0 <= x < GRID and 0 <= y < GRID):
        raise BadRequest(f"x and y must be whole numbers from 0 to {GRID - 1}")
    return x, y


def parse_pixels(raw):
    if not isinstance(raw, list) or len(raw) > MAX_PIXELS_PER_REQUEST:
        raise BadRequest(f"pixels must be a list of at most {MAX_PIXELS_PER_REQUEST} entries")
    pixels = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise BadRequest("each pixel must be [x, y, \"#rrggbb\"]")
        x, y = parse_cell(item[0], item[1])
        pixels.append((x, y, parse_color(item[2])))
    return pixels

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0b0d12">
<title>LED Wall</title>
<style>
:root{color-scheme:dark;--bg:#0b0d12;--card:#161a23;--line:#262c3a;--text:#f2f4f8;--muted:#8b93a7;--accent:#4da3ff}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);
 font:16px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
 padding:max(16px,env(safe-area-inset-top)) 16px max(16px,env(safe-area-inset-bottom))}
h1{font-size:22px;margin:12px 0 4px}
.sub{color:var(--muted);margin:0 0 20px;font-size:14px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.card{appearance:none;border:2px solid var(--line);background:var(--card);color:var(--text);
 border-radius:16px;min-height:150px;display:flex;flex-direction:column;align-items:center;
 justify-content:center;gap:10px;font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent}
.card:active{transform:scale(.97)}
.card.on{border-color:var(--accent);box-shadow:0 0 0 3px rgba(77,163,255,.25)}
.icon{font-size:44px;line-height:1}
.label{font-size:18px;font-weight:600}
.tag{font-size:12px;color:var(--accent);height:16px}
#status{margin-top:24px;font-size:13px;color:var(--muted)}
#status::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;
 background:#3ecf8e;margin-right:8px}
#status.bad::before{background:#ff5d5d}
</style></head>
<body>
<h1>LED Wall</h1>
<p class="sub">Tap a screen to show it on the panel.</p>
<div class="grid" id="grid"></div>
<div id="status">Connecting...</div>
<script>
const grid=document.getElementById('grid'),status=document.getElementById('status');
let state=null;
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e}
function draw(){
  grid.replaceChildren();
  state.screens.forEach(s=>{
    const b=el('button','card'+(s.name===state.active?' on':''));
    b.append(el('span','icon',s.icon),el('span','label',s.label),el('span','tag',s.name===state.active?'On screen':''));
    b.onclick=()=>pick(s);
    grid.appendChild(b);
  });
}
function ok(v){status.textContent=v?'Connected':'Cannot reach the display';status.className=v?'':'bad'}
async function load(){
  try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw 0;state=await r.json();draw();ok(true)}
  catch(e){ok(false)}
}
async function pick(s){
  try{
    const r=await fetch('/api/screen',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:s.name})});
    if(!r.ok)throw 0;state=await r.json();draw();ok(true);
    if(s.page)location.href=s.page;
  }catch(e){ok(false)}
}
load();setInterval(load,3000);
</script></body></html>
""".encode("utf-8")


class ControlServer:
    def __init__(self, manager, menu, port, host="0.0.0.0"):
        self._manager, self._menu = manager, tuple(menu)
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def _send(self, status, body, kind="application/json"):
                data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def _json_body(self):
                try:
                    length = int(self.headers.get("Content-Length", 0))
                except ValueError:
                    raise BadRequest("bad Content-Length")
                if length > MAX_BODY_BYTES:
                    raise BadRequest("body too large")
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                except ValueError:
                    raise BadRequest("body is not JSON")
                if not isinstance(body, dict):
                    raise BadRequest("body must be a JSON object")
                return body

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                if path in ("/", "/index.html"):
                    self._send(200, PAGE, "text/html; charset=utf-8")
                elif path == "/api/state":
                    self._send(200, outer.state())
                elif path == "/draw" and outer._freestyle():
                    self._send(200, DRAW_PAGE.encode("utf-8"), "text/html; charset=utf-8")
                elif path == "/api/draw/canvas.png" and outer._freestyle():
                    self._send(200, outer._freestyle().png(), "image/png")
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                path = self.path.split("?", 1)[0]
                try:
                    if path == "/api/screen":
                        return self._switch(self._json_body())
                    if path.startswith("/api/draw") and outer._freestyle():
                        return self._draw(path, self._json_body())
                    return self._send(404, {"error": "not found"})
                except BadRequest as exc:
                    return self._send(400, {"error": str(exc)})

            def _switch(self, body):
                name = body.get("name")
                if not isinstance(name, str):
                    raise BadRequest("send JSON like {\"name\": \"clock\"}")
                if name not in outer._menu:
                    return self._send(404, {"error": f"unknown screen: {name}"})
                outer._manager.set_active(name)
                log.info("screen switched to %s", name)
                self._send(200, outer.state())

            def _draw(self, path, body):
                screen = outer._freestyle()
                if path == "/api/draw":
                    stroke = body.get("stroke")
                    if stroke is not None and not isinstance(stroke, (int, float, str)):
                        raise BadRequest("stroke must be a number or text")
                    screen.draw(parse_pixels(body.get("pixels")), stroke=stroke)
                    return self._send(200, {"ok": True})
                if path == "/api/draw/fill":
                    x, y = parse_cell(body.get("x"), body.get("y"))
                    screen.flood(x, y, parse_color(body.get("color")))
                    return self._send(200, {"ok": True})
                if path == "/api/draw/clear":
                    screen.clear()
                    return self._send(200, {"ok": True})
                if path == "/api/draw/undo":
                    return self._send(200, {"ok": True, "undone": screen.undo()})
                return self._send(404, {"error": "not found"})

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer((host, port), Handler)

    def _freestyle(self):
        try:
            return self._manager.get("freestyle")
        except KeyError:
            return None

    @property
    def port(self):
        return self._server.server_address[1]

    def state(self):
        return {"active": self._manager.active, "screens": self._manager.describe(self._menu)}

    def start(self):
        threading.Thread(target=self._server.serve_forever, daemon=True, name="control").start()

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
