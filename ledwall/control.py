"""Phone control page: switch screens from a browser on your home network.

GET  /             the page
GET  /api/state    {"active": "bus", "brightness": 80, "screens": [{"name", "label", "icon", "page"?}, ...]}
POST /api/screen   {"name": "clock"}  -> same JSON as /api/state
POST /api/brightness {"value": 40}    -> same JSON (1-100)
POST /api/automation {"enabled": true} -> same JSON (turns the schedule on or off)
POST /api/pin {"name": "clock"}       -> same JSON (keep that screen on; {"name": null} unpins)

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
.cardwrap{position:relative}
.cardwrap .card{width:100%;height:100%}
.card.pinned{border-color:#f5a524}
.card.on.pinned{box-shadow:0 0 0 3px rgba(245,165,36,.25)}
.pin{appearance:none;position:absolute;top:8px;right:8px;width:38px;height:38px;border-radius:50%;
 border:2px solid var(--line);background:var(--bg);color:var(--text);font-size:17px;line-height:1;
 padding:0;cursor:pointer;opacity:.55;-webkit-tap-highlight-color:transparent}
.pin[aria-pressed=true]{opacity:1;border-color:#f5a524;background:rgba(245,165,36,.2)}
.card:active{transform:scale(.97)}
.card.on{border-color:var(--accent);box-shadow:0 0 0 3px rgba(77,163,255,.25)}
.icon{font-size:44px;line-height:1}
.label{font-size:18px;font-weight:600}
.tag{font-size:12px;color:var(--accent);height:16px}
.bright{margin-top:20px;background:var(--card);border:2px solid var(--line);border-radius:16px;padding:14px 16px}
.bright[hidden]{display:none}
.bhead{display:flex;justify-content:space-between;font-weight:600;margin-bottom:8px}
#bval{color:var(--accent)}
input[type=range]{width:100%;height:36px;accent-color:var(--accent);margin:0}
.presets{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:8px}
.presets button{appearance:none;border:2px solid var(--line);background:transparent;color:var(--text);
 border-radius:10px;padding:10px 0;font:inherit;font-size:14px;cursor:pointer;-webkit-tap-highlight-color:transparent}
.presets button:active{transform:scale(.96)}
.auto{margin-top:20px;background:var(--card);border:2px solid var(--line);border-radius:16px;padding:14px 16px}
.auto[hidden],.resume[hidden]{display:none}
.ahead{display:flex;justify-content:space-between;align-items:center;font-weight:600}
.switch{appearance:none;border:0;width:54px;height:32px;border-radius:16px;background:var(--line);
 position:relative;cursor:pointer;padding:0;transition:background .15s;-webkit-tap-highlight-color:transparent}
.switch span{position:absolute;top:3px;left:3px;width:26px;height:26px;border-radius:50%;background:#fff;transition:transform .15s}
.switch[aria-checked=true]{background:var(--accent)}
.switch[aria-checked=true] span{transform:translateX(22px)}
.astatus{margin-top:8px;font-size:14px;color:var(--muted)}
.resume{appearance:none;margin-top:10px;width:100%;border:2px solid var(--accent);background:transparent;color:var(--accent);
 border-radius:10px;padding:10px;font:inherit;font-weight:600;cursor:pointer}
#status{margin-top:24px;font-size:13px;color:var(--muted)}
#status::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;
 background:#3ecf8e;margin-right:8px}
#status.bad::before{background:#ff5d5d}
</style></head>
<body>
<h1>LED Wall</h1>
<p class="sub">Tap a screen to show it on the panel.</p>
<div class="grid" id="grid"></div>
<div class="auto" id="auto" hidden>
  <div class="ahead"><span>Automation</span>
    <button class="switch" id="autoSwitch" role="switch" aria-checked="false" aria-label="Automation"><span></span></button></div>
  <div class="astatus" id="astatus"></div>
  <button class="resume" id="autoResume" hidden>Resume automatic</button>
</div>
<div class="bright" id="bright" hidden>
  <div class="bhead"><span>Brightness</span><span id="bval">0%</span></div>
  <input type="range" id="bslider" min="5" max="100" step="5" value="50" aria-label="Brightness">
  <div class="presets">
    <button data-b="10">Night</button><button data-b="35">Dim</button>
    <button data-b="70">Day</button><button data-b="100">Max</button>
  </div>
</div>
<div id="status">Connecting...</div>
<script>
const grid=document.getElementById('grid'),status=document.getElementById('status');
let state=null;
const bright=document.getElementById('bright'),slider=document.getElementById('bslider'),bval=document.getElementById('bval');
let sliding=false,sendTimer=null;
const auto=document.getElementById('auto'),astatus=document.getElementById('astatus'),
      aswitch=document.getElementById('autoSwitch'),aresume=document.getElementById('autoResume');
function el(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e}
function draw(){
  grid.replaceChildren();
  const a=state.automation;
  state.screens.forEach(s=>{
    const pinned=!!a&&a.pinned===s.name;
    const wrap=el('div','cardwrap');
    const b=el('button','card'+(s.name===state.active?' on':'')+(pinned?' pinned':''));
    b.append(el('span','icon',s.icon),el('span','label',s.label),
             el('span','tag',pinned?'Pinned':(s.name===state.active?'On screen':'')));
    b.onclick=()=>pick(s);
    wrap.appendChild(b);
    if(a){
      const p=el('button','pin','📌');
      p.setAttribute('aria-pressed',pinned?'true':'false');
      p.setAttribute('aria-label',(pinned?'Unpin ':'Pin ')+s.label);
      p.onclick=e=>{e.stopPropagation();postPin(pinned?null:s.name)};
      wrap.appendChild(p);
    }
    grid.appendChild(wrap);
  });
}
async function postPin(name){
  try{
    const r=await fetch('/api/pin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    if(!r.ok)throw 0;state=await r.json();showAll();ok(true);
  }catch(e){ok(false)}
}
function labelOf(n){const s=state.screens.find(x=>x.name===n);return s?s.label:n}
function showAutomation(){
  const a=state.automation;
  if(!a){auto.hidden=true;return}
  auto.hidden=false;
  aswitch.setAttribute('aria-checked',a.enabled?'true':'false');
  let text;
  const pin=a.pinned?labelOf(a.pinned):null;
  if(!a.enabled)text='Off: the panel stays on the screen you pick.'+(pin?' (Pinned: '+pin+')':'');
  else if(a.holding)text='Manual: holding your choice'+(a.hold_minutes?' for '+a.hold_minutes+' more min':'')+(pin?', then back to pinned '+pin:'')+'.';
  else if(pin)text='Pinned: '+pin+'. It stays until you unpin it.';
  else{
    const names=a.plan.map(labelOf);
    text=(a.rotating?'Rotating '+names.join(' / ')+(a.seconds?' ('+a.seconds+' s each)':''):'Showing '+names[0])+(a.until?' until '+a.until:'');
  }
  astatus.textContent=text;
  aresume.hidden=!(a.enabled&&a.holding);
}
async function postAutomation(enabled){
  try{
    const r=await fetch('/api/automation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled})});
    if(!r.ok)throw 0;state=await r.json();showAll();ok(true);
  }catch(e){ok(false)}
}
aswitch.onclick=()=>postAutomation(!(state.automation&&state.automation.enabled));
aresume.onclick=()=>postAutomation(true);
function showAll(){draw();showBrightness();showAutomation()}
function showBrightness(){
  if(typeof state.brightness!=='number'){bright.hidden=true;return}
  bright.hidden=false;
  if(!sliding){slider.value=state.brightness;bval.textContent=state.brightness+'%'}
}
async function postBrightness(v){
  try{
    const r=await fetch('/api/brightness',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:+v})});
    if(!r.ok)throw 0;state=await r.json();ok(true);
  }catch(e){ok(false)}
}
slider.addEventListener('input',()=>{
  sliding=true;bval.textContent=slider.value+'%';
  if(!sendTimer)sendTimer=setTimeout(()=>{sendTimer=null;postBrightness(slider.value)},120);
});
slider.addEventListener('change',async()=>{
  clearTimeout(sendTimer);sendTimer=null;await postBrightness(slider.value);sliding=false;showBrightness();
});
document.querySelectorAll('.presets button').forEach(b=>b.onclick=async()=>{
  slider.value=b.dataset.b;bval.textContent=b.dataset.b+'%';await postBrightness(b.dataset.b);showBrightness();
});
function ok(v){status.textContent=v?'Connected':'Cannot reach the display';status.className=v?'':'bad'}
async function load(){
  try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw 0;state=await r.json();showAll();ok(true)}
  catch(e){ok(false)}
}
async function pick(s){
  try{
    const r=await fetch('/api/screen',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:s.name})});
    if(!r.ok)throw 0;state=await r.json();showAll();ok(true);
    if(s.page)location.href=s.page;
  }catch(e){ok(false)}
}
load();setInterval(load,3000);
</script></body></html>
""".encode("utf-8")


class ControlServer:
    def __init__(self, manager, menu, port, host="0.0.0.0", display=None, automation=None):
        # `display` (optional) has .brightness and .set_brightness(percent): the backend
        self._manager, self._menu, self._display = manager, tuple(menu), display
        self._automation = automation          # optional: the schedule (ledwall.automation)
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
                    if path == "/api/brightness" and outer._display:
                        return self._brightness(self._json_body())
                    if path == "/api/automation" and outer._automation:
                        return self._automation(self._json_body())
                    if path == "/api/pin" and outer._automation:
                        return self._pin(self._json_body())
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
                if outer._automation:
                    outer._automation.hold()          # a manual choice pauses the schedule
                outer._manager.set_active(name)
                log.info("screen switched to %s", name)
                self._send(200, outer.state())

            def _brightness(self, body):
                value = body.get("value")
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100:
                    raise BadRequest("value must be a whole number from 1 to 100")
                outer._display.set_brightness(value)
                log.info("brightness set to %d%%", value)
                self._send(200, outer.state())

            def _pin(self, body):
                if "name" not in body or not (body["name"] is None or isinstance(body["name"], str)):
                    raise BadRequest('send JSON like {"name": "clock"} or {"name": null}')
                name = body["name"]
                if name is None:
                    outer._automation.unpin()
                elif name in outer._menu:
                    outer._automation.pin(name)
                else:
                    return self._send(404, {"error": f"unknown screen: {name}"})
                self._send(200, outer.state())

            def _automation(self, body):
                enabled = body.get("enabled")
                if not isinstance(enabled, bool):
                    raise BadRequest('send JSON like {"enabled": true}')
                outer._automation.set_enabled(enabled)
                self._send(200, outer.state())

            def _draw(self, path, body):
                screen = outer._freestyle()
                if outer._automation:
                    outer._automation.hold()          # keep the schedule away while you draw
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
        state = {"active": self._manager.active, "screens": self._manager.describe(self._menu)}
        if self._display:
            state["brightness"] = self._display.brightness
        if self._automation:
            state["automation"] = self._automation.status()
        return state

    def start(self):
        threading.Thread(target=self._server.serve_forever, daemon=True, name="control").start()

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
