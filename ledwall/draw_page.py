"""The sketch page (served at /draw)."""

DRAW_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0b0d12">
<title>Draw</title>
<style>
:root{color-scheme:dark;--bg:#0b0d12;--card:#161a23;--line:#262c3a;--text:#f2f4f8;--muted:#8b93a7;--accent:#4da3ff}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);
 font:15px/1.3 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;overscroll-behavior:none}
body{padding:max(12px,env(safe-area-inset-top)) 12px max(12px,env(safe-area-inset-bottom));
 max-width:520px;margin:0 auto}
header{display:flex;align-items:center;gap:12px;margin-bottom:10px}
header a{color:var(--accent);text-decoration:none;font-size:15px}
header h1{font-size:18px;margin:0}
#status{margin-left:auto;font-size:12px;color:var(--muted)}
#status.bad{color:#ff5d5d}
.stage{position:relative;width:100%;aspect-ratio:1;border-radius:10px;overflow:hidden;
 border:2px solid var(--line);background:#000}
#cv{position:absolute;inset:0;width:100%;height:100%;image-rendering:pixelated;touch-action:none;cursor:crosshair}
#grid{position:absolute;inset:0;pointer-events:none;display:none;
 background-image:linear-gradient(to right,rgba(255,255,255,.10) 1px,transparent 1px),
 linear-gradient(to bottom,rgba(255,255,255,.10) 1px,transparent 1px);
 background-size:calc(100% / 64) calc(100% / 64)}
#grid.on{display:block}
.row{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
button{appearance:none;border:2px solid var(--line);background:var(--card);color:var(--text);
 border-radius:12px;padding:10px 12px;font:inherit;min-height:44px;cursor:pointer;
 -webkit-tap-highlight-color:transparent}
button:active{transform:scale(.96)}
button.on{border-color:var(--accent);box-shadow:0 0 0 2px rgba(77,163,255,.25)}
.tools button{flex:1}
.sizes button{width:48px;padding:0}
.palette{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-top:10px}
.sw{aspect-ratio:1;border-radius:50%;border:3px solid var(--line);padding:0;min-height:0}
.sw.on{border-color:#fff;box-shadow:0 0 0 2px var(--accent)}
input[type=color]{width:100%;height:100%;border:0;padding:0;background:none;opacity:0;position:absolute;inset:0}
.custom{position:relative;background:conic-gradient(red,yellow,lime,aqua,blue,magenta,red);overflow:hidden}
.actions button{flex:1}
</style></head>
<body>
<header><a href="/">&larr; Screens</a><h1>Draw</h1><span id="status">Connecting...</span></header>
<div class="stage"><canvas id="cv" width="64" height="64"></canvas><div id="grid"></div></div>
<div class="row tools" id="tools">
  <button data-tool="pen" class="on">&#9999;&#65039; Pen</button>
  <button data-tool="eraser">&#129529; Eraser</button>
  <button data-tool="fill">&#129699; Fill</button>
</div>
<div class="row sizes" id="sizes"><button data-size="1" class="on">1</button><button data-size="2">2</button><button data-size="3">3</button><button data-size="4">4</button><button id="gridbtn" style="width:auto;padding:0 14px">Grid</button></div>
<div class="palette" id="palette"></div>
<div class="row actions"><button id="undo">&#8617;&#65039; Undo</button><button id="clear">&#128465;&#65039; Clear</button></div>
<script>
const N=64,cv=document.getElementById('cv'),ctx=cv.getContext('2d'),statusEl=document.getElementById('status');
const COLORS=['#ff3b30','#ff9500','#ffcc00','#34c759','#00c7be','#0a84ff','#5e5ce6','#bf5af2','#ff2d92','#ffffff','#8e8e93','#000000'];
let tool='pen',size=1,color=COLORS[0],stroke=Date.now(),pending=[],last=null,drawing=false,flushTimer=null;

function setStatus(ok){statusEl.textContent=ok?'Live':'Cannot reach the display';statusEl.className=ok?'':'bad'}
async function api(path,body){
  try{
    const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});
    setStatus(r.ok);return r.ok?r.json():null;
  }catch(e){setStatus(false);return null}
}
function loadCanvas(){
  return new Promise(resolve=>{
    const img=new Image();
    img.onload=()=>{ctx.clearRect(0,0,N,N);ctx.drawImage(img,0,0);resolve()};
    img.onerror=()=>{setStatus(false);resolve()};
    img.src='/api/draw/canvas.png?'+Date.now();
  });
}
function cellOf(e){
  const r=cv.getBoundingClientRect();
  return [Math.max(0,Math.min(N-1,Math.floor((e.clientX-r.left)/r.width*N))),
          Math.max(0,Math.min(N-1,Math.floor((e.clientY-r.top)/r.height*N)))];
}
function plot(x,y){
  const c=tool==='eraser'?'#000000':color,half=Math.floor((size-1)/2);
  ctx.fillStyle=c;
  for(let dx=0;dx<size;dx++)for(let dy=0;dy<size;dy++){
    const px=x-half+dx,py=y-half+dy;
    if(px>=0&&px<N&&py>=0&&py<N){ctx.fillRect(px,py,1,1);pending.push([px,py,c])}
  }
}
function line(x0,y0,x1,y1){
  const dx=Math.abs(x1-x0),dy=-Math.abs(y1-y0),sx=x0<x1?1:-1,sy=y0<y1?1:-1;let err=dx+dy;
  for(;;){plot(x0,y0);if(x0===x1&&y0===y1)break;const e2=2*err;
    if(e2>=dy){err+=dy;x0+=sx}if(e2<=dx){err+=dx;y0+=sy}}
}
function scheduleFlush(){if(!flushTimer)flushTimer=setTimeout(flush,40)}
async function flush(){
  flushTimer=null;
  while(pending.length){const chunk=pending.splice(0,2000);await api('/api/draw',{stroke,pixels:chunk})}
}
cv.addEventListener('pointerdown',async e=>{
  e.preventDefault();
  if(cv.setPointerCapture)cv.setPointerCapture(e.pointerId);
  const [x,y]=cellOf(e);
  if(tool==='fill'){
    await flush();
    if(await api('/api/draw/fill',{x,y,color}))await loadCanvas();
    return;
  }
  drawing=true;stroke=Date.now()+Math.random();last=[x,y];plot(x,y);scheduleFlush();
});
cv.addEventListener('pointermove',e=>{
  if(!drawing)return;
  e.preventDefault();
  const events=e.getCoalescedEvents?e.getCoalescedEvents():[];
  for(const ev of (events.length?events:[e])){
    const [x,y]=cellOf(ev);
    if(x!==last[0]||y!==last[1]){line(last[0],last[1],x,y);last=[x,y]}
  }
  scheduleFlush();
});
function endStroke(){if(drawing){drawing=false;flush()}}
cv.addEventListener('pointerup',endStroke);
cv.addEventListener('pointercancel',endStroke);
cv.addEventListener('pointerleave',endStroke);

document.querySelectorAll('#tools button').forEach(b=>b.onclick=()=>{
  tool=b.dataset.tool;document.querySelectorAll('#tools button').forEach(x=>x.classList.toggle('on',x===b));});
document.querySelectorAll('#sizes button[data-size]').forEach(b=>b.onclick=()=>{
  size=+b.dataset.size;document.querySelectorAll('#sizes button[data-size]').forEach(x=>x.classList.toggle('on',x===b));});
document.getElementById('gridbtn').onclick=e=>{
  const on=document.getElementById('grid').classList.toggle('on');e.currentTarget.classList.toggle('on',on)};

const palette=document.getElementById('palette');
function pick(c,btn){
  color=c;if(tool==='eraser'){tool='pen';document.querySelectorAll('#tools button').forEach(x=>x.classList.toggle('on',x.dataset.tool==='pen'))}
  palette.querySelectorAll('.sw').forEach(x=>x.classList.toggle('on',x===btn));
}
COLORS.forEach((c,i)=>{
  const b=document.createElement('button');b.className='sw'+(i===0?' on':'');b.style.background=c;
  b.setAttribute('aria-label',c);b.onclick=()=>pick(c,b);palette.appendChild(b);
});
const custom=document.createElement('button');custom.className='sw custom';custom.setAttribute('aria-label','Custom color');
const picker=document.createElement('input');picker.type='color';picker.value='#ff3b30';
picker.oninput=()=>pick(picker.value,custom);custom.appendChild(picker);palette.appendChild(custom);

document.getElementById('undo').onclick=async()=>{await flush();if(await api('/api/draw/undo'))await loadCanvas()};
document.getElementById('clear').onclick=async()=>{
  if(!confirm('Clear the whole canvas?'))return;
  await flush();if(await api('/api/draw/clear')){ctx.fillStyle='#000';ctx.fillRect(0,0,N,N)}
};

(async()=>{
  await api('/api/screen',{name:'freestyle'});
  await loadCanvas();
})();
</script></body></html>
"""
