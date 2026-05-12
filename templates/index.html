<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Research Hub</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#07070f;color:#ddd;font-family:'Courier New',monospace;height:100vh;overflow:hidden}
/* TOPBAR */
#topbar{position:fixed;top:0;left:0;right:0;height:44px;z-index:100;display:flex;align-items:center;padding:0 16px;gap:12px;background:#07070fee;border-bottom:1px solid #14142a}
.logo{font-size:12px;letter-spacing:.12em;color:#555;flex-shrink:0}.logo b{color:#7f77dd;font-weight:normal}
.stats-row{display:flex;gap:1px;flex:1;max-width:480px;margin:0 auto}
.stat{flex:1;text-align:center;padding:3px 6px;background:#0d0d1e;border-radius:3px}
.stat-n{font-size:15px;font-weight:bold}
.pu{color:#7f77dd}.te{color:#1d9e75}.am{color:#ba7517}.bl{color:#378add}
.stat-l{font-size:8px;color:#444;letter-spacing:.06em}
.topbar-r{display:flex;align-items:center;gap:8px;margin-left:auto}
.live{display:flex;align-items:center;gap:5px;font-size:10px;color:#1d9e75}
.ldot{width:6px;height:6px;border-radius:50%;background:#1d9e75;animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.15}}
.add-btn{font-size:10px;padding:4px 12px;border-radius:4px;border:1px solid #7f77dd60;background:#7f77dd15;color:#7f77dd;cursor:pointer;font-family:inherit;transition:all .2s;letter-spacing:.05em}
.add-btn:hover{background:#7f77dd28}
.dl-btn{font-size:10px;padding:4px 12px;border-radius:4px;border:1px solid #1d9e7560;background:#1d9e7515;color:#1d9e75;cursor:pointer;font-family:inherit;transition:all .2s}
.dl-btn:hover{background:#1d9e7528}
/* CANVAS */
#c{position:fixed;top:44px;left:0;display:block}
/* SIDEBAR */
#sb{position:fixed;right:0;top:44px;bottom:28px;width:260px;background:#0d0d1e;border-left:1px solid #14142a;display:flex;flex-direction:column;overflow:hidden}
.tabs{display:flex;border-bottom:1px solid #14142a;flex-shrink:0}
.tab{flex:1;padding:8px 4px;font-size:9px;letter-spacing:.07em;color:#444;cursor:pointer;text-align:center;border-bottom:2px solid transparent;transition:all .15s}
.tab.on{color:#ddd;border-color:#7f77dd}
.panel{display:none;flex:1;overflow-y:auto;flex-direction:column}
.panel.on{display:flex}
.panel::-webkit-scrollbar{width:2px}
.panel::-webkit-scrollbar-thumb{background:#1a1a2e}
/* AGENT CARDS */
.acard{margin:5px 8px;border-radius:6px;border:1px solid #14142a;background:#0a0a14;overflow:hidden;transition:border-color .2s}
.acard:hover{border-color:#1e1e3e}
.acard.active{border-color:#1d9e7530}.acard.rate_limited{border-color:#ba751730}
.actop{display:flex;align-items:center;gap:8px;padding:8px 10px;cursor:pointer}
.acicon{width:28px;height:28px;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.acinfo{flex:1;min-width:0}
.acname{font-size:11px;color:#ccc}
.acmodel{font-size:9px;color:#444;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:1px}
.acbadge{font-size:9px;padding:2px 6px;border-radius:3px;flex-shrink:0}
.acbadge.active{background:#0f3d2a;color:#1d9e75}
.acbadge.rate_limited{background:#3d2a0f;color:#ba7517}
.acbadge.unknown{background:#14142a;color:#444}
.acdet{border-top:1px solid #14142a;padding:8px 10px;display:none;font-size:9px;color:#444;line-height:1.9}
.acdet.show{display:block}.acdet span{color:#7f77dd}
/* FEED */
.fitem{display:flex;gap:7px;padding:7px 10px;border-bottom:1px solid #10101e}
.fdot{width:5px;height:5px;border-radius:50%;margin-top:5px;flex-shrink:0}
.fbody{flex:1;min-width:0}
.ftext{font-size:10px;color:#666;line-height:1.5}
.ftext strong{color:#aaa;font-weight:normal}
.ftime{font-size:9px;color:#2a2a3e}
/* INSIGHTS */
.icard{margin:5px 8px;border-radius:6px;border:1px solid #14142a;background:#0a0a14;padding:10px;cursor:pointer}
.icard:hover{border-color:#1e1e3e}
.iscore{font-size:9px;padding:1px 6px;border-radius:3px;display:inline-block;margin-bottom:5px}
.itext{font-size:10px;color:#666;line-height:1.6}
/* BOTTOM BAR */
#botbar{position:fixed;bottom:0;left:0;right:260px;height:28px;z-index:100;display:flex;align-items:center;padding:0 12px;gap:5px;background:#07070fee;border-top:1px solid #14142a}
.fl{font-size:9px;color:#444;letter-spacing:.07em;margin-right:2px}
.fbtn{font-size:9px;padding:2px 9px;border-radius:3px;border:1px solid #14142a;background:transparent;color:#444;cursor:pointer;font-family:inherit;transition:all .15s}
.fbtn.on{background:#14142a;color:#ddd;border-color:#1e1e3e}
#bc{margin-left:auto;font-size:9px;color:#333}
/* POPUP */
#popup{position:fixed;z-index:500;background:#0d0d1e;border:1px solid #2a2a5e;border-radius:12px;width:500px;max-height:78vh;box-shadow:0 30px 80px #000000a0;display:none;flex-direction:column;transition:opacity .2s,transform .2s;opacity:0;transform:translateY(10px) scale(.97)}
#popup.show{opacity:1;transform:none}
.ph{padding:16px 18px 12px;border-bottom:1px solid #14142a;flex-shrink:0}
.ptop{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.pagent{font-size:9px;padding:3px 9px;border-radius:99px;display:inline-block;margin-bottom:8px;border:1px solid}
.ptopic{font-size:14px;color:#ddd;line-height:1.4;font-weight:500}
.pmeta{font-size:10px;color:#444;margin-top:5px;display:flex;align-items:center;gap:8px}
.pscore{font-size:10px;padding:2px 8px;border-radius:3px}
.pscore.hi{background:#0f3d2a;color:#1d9e75}.pscore.mi{background:#3d2a0f;color:#ba7517}.pscore.lo{background:#14142a;color:#444}
.pclose{background:none;border:1px solid #14142a;color:#555;padding:5px 12px;border-radius:5px;cursor:pointer;font-family:inherit;font-size:11px;transition:all .15s;flex-shrink:0}
.pclose:hover{color:#ddd;border-color:#2a2a4e;background:#14142a}
.pbody{padding:14px 18px;overflow-y:auto;flex:1}
.pbody::-webkit-scrollbar{width:3px}
.pbody::-webkit-scrollbar-thumb{background:#1a1a2e}
.pcontent{font-size:11px;color:#777;line-height:1.95;white-space:pre-wrap}
/* MODAL */
.moverlay{position:fixed;inset:0;z-index:600;background:#00000090;backdrop-filter:blur(6px);display:none;align-items:center;justify-content:center}
.moverlay.show{display:flex}
.modal{background:#0d0d1e;border:1px solid #1e1e3e;border-radius:14px;padding:28px;width:480px;box-shadow:0 40px 100px #000000a0}
.mtitle{font-size:15px;color:#ddd;margin-bottom:5px}
.msub{font-size:10px;color:#555;margin-bottom:22px;line-height:1.7}
.field{margin-bottom:14px}
.field label{display:block;font-size:9px;color:#555;letter-spacing:.08em;margin-bottom:5px}
.field input,.field select,.field textarea{width:100%;background:#07070f;border:1px solid #1e1e3e;color:#ddd;padding:9px 12px;border-radius:6px;font-family:inherit;font-size:12px;outline:none;transition:border-color .2s}
.field input:focus,.field select:focus,.field textarea:focus{border-color:#7f77dd60}
.field textarea{resize:vertical;min-height:65px}
.field select option{background:#0d0d1e}
.color-row{display:flex;gap:8px;flex-wrap:wrap}
.cswatch{width:24px;height:24px;border-radius:50%;cursor:pointer;border:2px solid transparent;transition:border-color .15s}
.cswatch.sel{border-color:#fff}
.mbtns{display:flex;gap:10px;justify-content:flex-end;margin-top:22px}
.mcancel{background:none;border:1px solid #1e1e3e;color:#666;padding:8px 18px;border-radius:6px;cursor:pointer;font-family:inherit;font-size:11px}
.mcancel:hover{color:#ddd}
.msave{background:#7f77dd20;border:1px solid #7f77dd60;color:#7f77dd;padding:8px 18px;border-radius:6px;cursor:pointer;font-family:inherit;font-size:11px;transition:all .15s}
.msave:hover{background:#7f77dd35}
#hint{position:fixed;bottom:36px;left:50%;transform:translateX(-50%);font-size:10px;color:#2a2a4e;pointer-events:none;letter-spacing:.07em;transition:opacity 2s;z-index:50}
</style>
</head>
<body>

<div id="topbar">
  <div class="logo">// <b>AGENT</b> RESEARCH HUB</div>
  <div class="stats-row">
    <div class="stat"><div class="stat-n pu" id="s-total">—</div><div class="stat-l">RESULTS</div></div>
    <div class="stat"><div class="stat-n te" id="s-active">—</div><div class="stat-l">ACTIVE</div></div>
    <div class="stat"><div class="stat-n am" id="s-topics">—</div><div class="stat-l">TOPICS</div></div>
    <div class="stat"><div class="stat-n bl" id="s-time">—</div><div class="stat-l">CLOCK</div></div>
  </div>
  <div class="topbar-r">
    <div class="live"><div class="ldot"></div><span id="tick">LIVE</span></div>
    <button class="dl-btn" onclick="downloadData()">↓ EXPORT</button>
    <button class="add-btn" onclick="openModal()">+ ADD AGENT</button>
  </div>
</div>

<canvas id="c"></canvas>

<div id="sb">
  <div class="tabs">
    <div class="tab on" onclick="showTab('agents',this)">AGENTS</div>
    <div class="tab" onclick="showTab('feed',this)">ACTIVITY</div>
    <div class="tab" onclick="showTab('insights',this)">INSIGHTS</div>
  </div>
  <div class="panel on" id="tab-agents"></div>
  <div class="panel" id="tab-feed"></div>
  <div class="panel" id="tab-insights"></div>
</div>

<div id="botbar">
  <span class="fl">FILTER</span>
  <button class="fbtn on" onclick="setFilter('all',this)">All</button>
  <button class="fbtn" onclick="setFilter('market_scout',this)">Scout</button>
  <button class="fbtn" onclick="setFilter('trend_analyst',this)">Analyst</button>
  <button class="fbtn" onclick="setFilter('deep_diver',this)">Diver</button>
  <button class="fbtn" onclick="setFilter('critic',this)">Critic</button>
  <button class="fbtn" onclick="setFilter('memory',this)">Memory</button>
  <span id="bc"></span>
</div>

<div id="popup">
  <div class="ph">
    <div class="ptop">
      <div style="flex:1;min-width:0">
        <div id="p-badge"></div>
        <div class="ptopic" id="p-topic"></div>
        <div class="pmeta"><span id="p-date"></span><span id="p-score"></span></div>
      </div>
      <button class="pclose" id="closebtn">✕ close</button>
    </div>
  </div>
  <div class="pbody"><div class="pcontent" id="p-content"></div></div>
</div>

<div class="moverlay" id="modal">
  <div class="modal">
    <div class="mtitle">Add New Research Agent</div>
    <div class="msub">New agent will be added to your GitHub repo and auto-deploy on Render. Give it a name, describe what it researches, pick an AI provider and paste your API key.</div>
    <div class="field"><label>AGENT NAME</label><input id="m-name" placeholder="e.g. Competitor Analyst" maxlength="30"></div>
    <div class="field"><label>WHAT IT RESEARCHES</label><textarea id="m-role" placeholder="e.g. Finds direct competitors, analyzes their weaknesses and pricing gaps"></textarea></div>
    <div class="field"><label>AI PROVIDER</label>
      <select id="m-provider">
        <option value="groq">Groq — Llama 3.3 70B (free)</option>
        <option value="gemini">Google Gemini 2.0 Flash (free)</option>
        <option value="openrouter">OpenRouter — Nemotron (free)</option>
      </select>
    </div>
    <div class="field"><label>API KEY</label><input id="m-key" type="password" placeholder="Paste your API key"></div>
    <div class="field"><label>COLOR</label>
      <div class="color-row" id="color-row">
        <div class="cswatch sel" style="background:#7f77dd" data-c="#7f77dd" onclick="selC(this)"></div>
        <div class="cswatch" style="background:#378add" data-c="#378add" onclick="selC(this)"></div>
        <div class="cswatch" style="background:#1d9e75" data-c="#1d9e75" onclick="selC(this)"></div>
        <div class="cswatch" style="background:#d85a30" data-c="#d85a30" onclick="selC(this)"></div>
        <div class="cswatch" style="background:#ba7517" data-c="#ba7517" onclick="selC(this)"></div>
        <div class="cswatch" style="background:#d4537e" data-c="#d4537e" onclick="selC(this)"></div>
        <div class="cswatch" style="background:#2ab5b5" data-c="#2ab5b5" onclick="selC(this)"></div>
        <div class="cswatch" style="background:#a0c040" data-c="#a0c040" onclick="selC(this)"></div>
      </div>
    </div>
    <div class="mbtns">
      <button class="mcancel" onclick="closeModal()">Cancel</button>
      <button class="msave" onclick="saveAgent()">Add Agent →</button>
    </div>
  </div>
</div>

<div id="hint">↑ click any glowing bubble to read the research</div>

<script>
// ── DATA ──────────────────────────────────────────────────────
const AGENTS_DEF = [
  {key:'market_scout',  name:'Scout',   color:'#378add', icon:'🔍', fb:['Primary: Gemini','→ Fallback: Groq']},
  {key:'trend_analyst', name:'Analyst', color:'#1d9e75', icon:'📈', fb:['Primary: Groq','→ Fallback: Gemini']},
  {key:'deep_diver',    name:'Diver',   color:'#7f77dd', icon:'🧠', fb:['Primary: Nemotron','→ Fallback 1: QwQ','→ Fallback 2: Gemini']},
  {key:'critic',        name:'Critic',  color:'#d85a30', icon:'⚡', fb:['Primary: Groq']},
  {key:'memory',        name:'Memory',  color:'#ba7517', icon:'💾', fb:['Primary: Gemini']},
  {key:'synthesis',     name:'Synth',   color:'#d4537e', icon:'✨', fb:['Every Sunday 09:00']},
];

let agents = [...AGENTS_DEF];
const COL = {};
const updateColors = () => agents.forEach(a => COL[a.key] = a.color);
updateColors();

let statuses={}, allResults=[], allInsights=[], feedLog=[];
let bubbles=[], robots=[], particles=[], frame=0, hovered=null;
let activeFilter='all', selColor='#7f77dd';

// ── CANVAS SETUP ──────────────────────────────────────────────
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');

function resizeCanvas() {
  cv.width  = window.innerWidth - 260;
  cv.height = window.innerHeight - 44 - 28;
}
resizeCanvas();
window.addEventListener('resize', () => { resizeCanvas(); placeRobots(); });

// ── ROBOTS ────────────────────────────────────────────────────
class Robot {
  constructor(def, x, y) {
    this.key   = def.key;
    this.name  = def.name;
    this.color = def.color;
    this.icon  = def.icon || '🤖';
    this.x = x; this.y = y; this.tx = x; this.ty = y;
    this.status = 'unknown';
    this.p = Math.random() * Math.PI * 2;
    this.w = Math.random() * Math.PI * 2;
  }

  tick() {
    this.p += 0.03; this.w += 0.017;
    this.x += (this.tx - this.x) * 0.05;
    this.y += (this.ty - this.y) * 0.05;
  }

  draw() {
    const { x, y, color: c, status: s, p, w } = this;
    const active = s === 'active', lim = s === 'rate_limited';
    const bob = active ? Math.sin(w) * 3 : 0;
    const wy = y + bob;
    const glow = active ? 0.65 + 0.25 * Math.sin(p) : 0.2;

    ctx.save();
    ctx.globalAlpha = lim ? 0.35 : 1;

    // outer halo
    if (active) {
      ctx.globalAlpha = 0.08 + 0.05 * Math.sin(p);
      ctx.fillStyle = c;
      ctx.beginPath(); ctx.arc(x, wy, 52, 0, Math.PI*2); ctx.fill();
      ctx.globalAlpha = lim ? 0.35 : 1;
    }

    // platform
    ctx.fillStyle = '#0c0c1e'; ctx.strokeStyle = c + '35'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.roundRect(x-36, wy+24, 72, 10, 3); ctx.fill(); ctx.stroke();

    // body
    ctx.fillStyle = '#0a0a1c'; ctx.strokeStyle = c; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.roundRect(x-13, wy-12, 26, 24, 5); ctx.fill(); ctx.stroke();

    // head
    ctx.beginPath(); ctx.roundRect(x-10, wy-25, 20, 15, 4); ctx.fill(); ctx.stroke();

    // antenna (active only)
    if (active) {
      ctx.globalAlpha = 0.6 + 0.3 * Math.sin(p * 1.7);
      ctx.strokeStyle = c; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, wy-25); ctx.lineTo(x, wy-34); ctx.stroke();
      ctx.fillStyle = c;
      ctx.beginPath(); ctx.arc(x, wy-36, 3, 0, Math.PI*2); ctx.fill();
      ctx.globalAlpha = 0.15;
      ctx.beginPath(); ctx.arc(x, wy-36, 7, 0, Math.PI*2); ctx.fill();
      ctx.globalAlpha = lim ? 0.35 : 1;
    }

    // eyes
    ctx.globalAlpha = glow; ctx.fillStyle = c;
    ctx.beginPath(); ctx.arc(x-3.5, wy-18, 2.3, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.arc(x+3.5, wy-18, 2.3, 0, Math.PI*2); ctx.fill();

    // legs
    ctx.globalAlpha = active ? 0.8 : 0.2; ctx.strokeStyle = c; ctx.lineWidth = 2;
    const sw = active ? Math.sin(p*2)*5 : 0;
    ctx.beginPath(); ctx.moveTo(x-5, wy+12); ctx.lineTo(x-5-sw, wy+24); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x+5, wy+12); ctx.lineTo(x+5+sw, wy+24); ctx.stroke();

    // arms
    ctx.globalAlpha = active ? 0.8 : 0.2;
    const aw = active ? Math.sin(p*2+1)*7 : 0;
    ctx.beginPath(); ctx.moveTo(x-13, wy-1); ctx.lineTo(x-21-aw, wy+6); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x+13, wy-1); ctx.lineTo(x+21+aw, wy+6); ctx.stroke();

    // status dot
    ctx.globalAlpha = 1;
    ctx.fillStyle = active ? '#1d9e75' : lim ? '#ba7517' : '#1a1a2e';
    ctx.shadowColor = active ? '#1d9e75' : 'transparent';
    ctx.shadowBlur = active ? 8 : 0;
    ctx.beginPath(); ctx.arc(x+9, wy-4, 2.8, 0, Math.PI*2); ctx.fill();
    ctx.shadowBlur = 0;

    // name label
    ctx.globalAlpha = 0.5; ctx.fillStyle = '#777';
    ctx.font = '9px Courier New'; ctx.textAlign = 'center';
    ctx.fillText(this.name, x, wy+42);

    ctx.restore();
  }
}

function placeRobots() {
  const W = cv.width, H = cv.height;
  const slots = [
    {key:'market_scout',  x: W*0.13, y: H*0.26},
    {key:'trend_analyst', x: W*0.35, y: H*0.60},
    {key:'deep_diver',    x: W*0.60, y: H*0.24},
    {key:'critic',        x: W*0.80, y: H*0.52},
    {key:'memory',        x: W*0.90, y: H*0.20},
    {key:'synthesis',     x: W*0.50, y: H*0.80},
  ];
  const extras = [
    {x:W*0.22,y:H*0.75},{x:W*0.72,y:H*0.80},
    {x:W*0.05,y:H*0.55},{x:W*0.45,y:H*0.45},
  ];
  let ei = 0;

  if (robots.length === 0) {
    robots = agents.map(d => {
      const slot = slots.find(s => s.key === d.key) || extras[ei++] || {x:W*0.5,y:H*0.5};
      return new Robot(d, slot.x, slot.y);
    });
  } else {
    robots.forEach(r => {
      const slot = slots.find(s => s.key === r.key) || extras[ei++];
      if (slot) { r.tx = slot.x; r.ty = slot.y; }
    });
  }
}

// ── BUBBLES ───────────────────────────────────────────────────
class Bubble {
  constructor(res, x, y) {
    this.res   = res;
    this.x = x; this.y = y;
    this.vx = (Math.random() - 0.5) * 0.2;
    this.vy = (Math.random() - 0.5) * 0.2;
    this.color = COL[res.agent] || '#2a2a6e';
    this.p   = Math.random() * Math.PI * 2;
    this.age = 0;
    this.rad = 7 + Math.min(14, (res.score || 0) * 1.5);
    this.conn = [];
    this.label = (res.topic || '')
      .replace(/20\d\d[-–]?\d{0,4}/g, '')
      .replace(/\b(apps?|tool|platform|gaps?|market|people|why|do)\b/gi, '')
      .replace(/\s+/g, ' ').trim().slice(0, 20);
  }

  tick(W, H) {
    this.p += 0.02; this.age++;
    this.x += this.vx; this.y += this.vy;
    if (this.x < 20) this.vx += 0.05;
    if (this.x > W - 20) this.vx -= 0.05;
    if (this.y < 14) this.vy += 0.05;
    if (this.y > H - 14) this.vy -= 0.05;
    this.vx *= 0.997; this.vy *= 0.997;
  }

  draw(hov) {
    const { x, y, rad: r, color: c, p, age, label } = this;
    const fi = Math.min(1, age / 50);
    const g  = hov ? 1 : 0.4 + 0.15 * Math.sin(p);

    ctx.save();
    // glow rings
    ctx.globalAlpha = fi * g * 0.10;
    ctx.fillStyle = c;
    ctx.beginPath(); ctx.arc(x, y, r+12, 0, Math.PI*2); ctx.fill();
    ctx.globalAlpha = fi * g * 0.07;
    ctx.beginPath(); ctx.arc(x, y, r+6, 0, Math.PI*2); ctx.fill();

    // bubble fill
    ctx.globalAlpha = fi * (hov ? 0.88 : 0.50);
    ctx.fillStyle = c + '18'; ctx.strokeStyle = c + (hov ? 'cc' : '55');
    ctx.lineWidth = hov ? 1.8 : 0.9;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2); ctx.fill(); ctx.stroke();

    // core dot
    ctx.globalAlpha = fi * (hov ? 1 : g * 0.9);
    ctx.fillStyle = c; ctx.shadowColor = c; ctx.shadowBlur = hov ? 10 : 4;
    ctx.beginPath(); ctx.arc(x, y, r * 0.22, 0, Math.PI*2); ctx.fill();
    ctx.shadowBlur = 0;

    // hover pulse ring
    if (hov) {
      ctx.globalAlpha = 0.2 + 0.18 * Math.sin(p * 3);
      ctx.strokeStyle = c; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(x, y, r+18, 0, Math.PI*2); ctx.stroke();
    }

    // label pill
    if (hov || r > 11) {
      const lw = label.length * 5.3 + 14;
      ctx.globalAlpha = fi * (hov ? 1 : 0.8);
      ctx.shadowBlur = 0;
      ctx.fillStyle = '#07070f'; ctx.strokeStyle = c + (hov ? '80' : '35'); ctx.lineWidth = 0.6;
      ctx.beginPath(); ctx.roundRect(x - lw/2, y + r + 5, lw, 14, 3); ctx.fill(); ctx.stroke();
      ctx.fillStyle = hov ? c : c + 'cc';
      ctx.font = (hov ? '9' : '8') + 'px Courier New'; ctx.textAlign = 'center';
      ctx.fillText(label, x, y + r + 14);
    }
    ctx.restore();
  }

  hit(mx, my) {
    const dx = mx - this.x, dy = my - this.y;
    return Math.sqrt(dx*dx + dy*dy) <= this.rad + 12;
  }
}

function addBubble(res) {
  const W = cv.width, H = cv.height;
  const rb = robots.find(r => r.key === res.agent);
  let x, y;
  if (rb) {
    x = rb.x + (Math.random() - 0.5) * 160;
    y = rb.y + (Math.random() - 0.5) * 140;
  } else {
    x = 40 + Math.random() * (W - 80);
    y = 20 + Math.random() * (H - 40);
  }
  x = Math.max(20, Math.min(W - 20, x));
  y = Math.max(14, Math.min(H - 14, y));

  const b = new Bubble(res, x, y);

  // same-agent cluster links
  bubbles.filter(e => e.res.agent === res.agent).slice(-8).forEach(e => {
    const dx = e.x - x, dy = e.y - y;
    if (Math.sqrt(dx*dx + dy*dy) < 180 && b.conn.length < 2) {
      b.conn.push({node: e, type: 'cluster'});
    }
  });
  // cross-agent same-topic links (Obsidian relevance)
  bubbles.filter(e => e.res.agent !== res.agent && e.res.topic === res.topic).forEach(e => {
    if (b.conn.length < 5) b.conn.push({node: e, type: 'relevant'});
  });

  bubbles.push(b);
  if (bubbles.length > 140) bubbles.shift();
}

function seedBubbles(data) {
  bubbles = [];
  // Max 22 per agent for even distribution
  const byAgent = {};
  data.forEach(r => {
    if (!byAgent[r.agent]) byAgent[r.agent] = [];
    byAgent[r.agent].push(r);
  });
  let seeded = [];
  Object.values(byAgent).forEach(g => seeded.push(...g.slice(0, 22)));
  seeded.sort(() => Math.random() - 0.5);
  seeded.forEach((r, i) => setTimeout(() => addBubble(r), i * 18));
}

// ── PARTICLES ─────────────────────────────────────────────────
class Particle {
  constructor(x, y, tx, ty, c, type) {
    this.x = x; this.y = y; this.sx = x; this.sy = y;
    this.tx = tx; this.ty = ty; this.c = c; this.type = type || 'data';
    this.p = 0; this.spd = 0.007 + Math.random() * 0.005; this.done = false;
    this.sz = type === 'msg' ? 4.5 : 1.8 + Math.random() * 1.5;
    this.trail = [];
  }
  tick() {
    this.p += this.spd;
    if (this.p >= 1) { this.done = true; return; }
    const t = this.p, arc = this.type === 'msg' ? 70 : 45;
    const nx = this.sx + (this.tx - this.sx) * t;
    const ny = this.sy + (this.ty - this.sy) * t - Math.sin(t * Math.PI) * arc;
    if (this.type === 'msg') this.trail.push({x: nx, y: ny});
    if (this.trail.length > 10) this.trail.shift();
    this.x = nx; this.y = ny;
  }
  draw() {
    ctx.save();
    if (this.type === 'msg') {
      this.trail.forEach((tr, i) => {
        ctx.globalAlpha = (i / this.trail.length) * 0.22 * (1 - this.p);
        ctx.fillStyle = this.c;
        ctx.beginPath(); ctx.arc(tr.x, tr.y, this.sz * 0.45, 0, Math.PI*2); ctx.fill();
      });
      ctx.globalAlpha = (1 - this.p) * 0.9;
      ctx.fillStyle = this.c + '20'; ctx.strokeStyle = this.c; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.roundRect(this.x-5, this.y-4, 10, 8, 2); ctx.fill(); ctx.stroke();
      ctx.fillStyle = this.c; ctx.globalAlpha = (1 - this.p);
      ctx.beginPath(); ctx.arc(this.x, this.y, 1.5, 0, Math.PI*2); ctx.fill();
    } else {
      ctx.globalAlpha = (1 - this.p) * 0.85;
      ctx.fillStyle = this.c; ctx.shadowColor = this.c; ctx.shadowBlur = 4;
      ctx.beginPath(); ctx.arc(this.x, this.y, this.sz, 0, Math.PI*2); ctx.fill();
    }
    ctx.restore();
  }
}

function spark(fk, tk, type) {
  const f = robots.find(r => r.key === fk);
  const t = robots.find(r => r.key === tk);
  if (f && t) particles.push(new Particle(f.x, f.y, t.x, t.y, COL[fk] || f.color, type || 'data'));
}

const PIPE = [
  ['market_scout','trend_analyst'],['trend_analyst','deep_diver'],
  ['deep_diver','critic'],['critic','memory'],
  ['critic','synthesis'],['memory','market_scout'],
];

function drawPipeline() {
  PIPE.forEach(([a,b]) => {
    const ra = robots.find(r=>r.key===a), rb = robots.find(r=>r.key===b);
    if (!ra || !rb) return;
    ctx.save();
    ctx.strokeStyle = ra.status === 'active' ? COL[a] + '22' : '#12122a';
    ctx.lineWidth = ra.status === 'active' ? 1 : 0.6;
    ctx.setLineDash([3, 12]);
    ctx.beginPath(); ctx.moveTo(ra.x, ra.y); ctx.lineTo(rb.x, rb.y); ctx.stroke();
    ctx.restore();
  });
}

function drawConnections() {
  bubbles.forEach(b => {
    b.conn.forEach(({node: o, type}) => {
      if (!bubbles.includes(o)) return;
      ctx.save();
      if (type === 'relevant') {
        ctx.strokeStyle = b.color + '55'; ctx.lineWidth = 0.9; ctx.setLineDash([1,5]);
        ctx.beginPath(); ctx.moveTo(b.x,b.y); ctx.lineTo(o.x,o.y); ctx.stroke();
        ctx.setLineDash([]); ctx.globalAlpha = 0.45; ctx.fillStyle = b.color;
        ctx.beginPath(); ctx.arc((b.x+o.x)/2,(b.y+o.y)/2, 2, 0, Math.PI*2); ctx.fill();
      } else {
        ctx.strokeStyle = b.color + '14'; ctx.lineWidth = 0.4; ctx.setLineDash([2,9]);
        ctx.beginPath(); ctx.moveTo(b.x,b.y); ctx.lineTo(o.x,o.y); ctx.stroke();
      }
      ctx.restore();
    });
  });
}

// ── MOUSE ─────────────────────────────────────────────────────
let mx = -999, my = -999;
cv.addEventListener('mousemove', e => {
  const r = cv.getBoundingClientRect();
  mx = e.clientX - r.left; my = e.clientY - r.top;
  hovered = [...bubbles].reverse().find(b => b.hit(mx, my)) || null;
  cv.style.cursor = hovered ? 'pointer' : 'default';
});

cv.addEventListener('click', e => {
  const r = cv.getBoundingClientRect();
  const hit = [...bubbles].reverse().find(b => b.hit(e.clientX - r.left, e.clientY - r.top));
  if (hit) {
    openPopup(hit.res, e.clientX, e.clientY);
    document.getElementById('hint').style.opacity = '0';
  }
});

// ── POPUP ─────────────────────────────────────────────────────
function openPopup(res, cx, cy) {
  const sc = res.score || 0;
  const cls = sc >= 7 ? 'hi' : sc >= 4 ? 'mi' : 'lo';
  const ac = COL[res.agent] || '#7f77dd';
  const def = agents.find(a => a.key === res.agent);

  document.getElementById('p-badge').innerHTML =
    `<span class="pagent" style="background:${ac}18;color:${ac};border-color:${ac}40">${def?.icon||'🤖'} ${res.agent||''}</span>`;
  document.getElementById('p-topic').textContent = res.topic || '';
  document.getElementById('p-date').textContent = (res.created_at||'').slice(0,16).replace('T',' ');
  document.getElementById('p-score').innerHTML = sc > 0
    ? `<span class="pscore ${cls}">${sc}/10</span>` : '';
  document.getElementById('p-content').textContent = res.content || '';

  const pop = document.getElementById('popup');
  pop.style.display = 'flex';
  requestAnimationFrame(() => pop.classList.add('show'));

  const pw = 500, ph = Math.min(window.innerHeight * 0.76, 540);
  let px = cx + 18, py = cy - 40;
  if (px + pw > window.innerWidth - 270) px = cx - pw - 18;
  if (py + ph > window.innerHeight - 8) py = window.innerHeight - ph - 8;
  if (py < 8) py = 8;
  px = Math.max(8, px);
  pop.style.left = px + 'px';
  pop.style.top  = py + 'px';
}

function closePopup() {
  const pop = document.getElementById('popup');
  pop.classList.remove('show');
  setTimeout(() => { pop.style.display = 'none'; }, 220);
}

document.getElementById('closebtn').addEventListener('click', closePopup);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePopup(); });

// ── MAIN LOOP ─────────────────────────────────────────────────
function loop() {
  ctx.clearRect(0, 0, cv.width, cv.height);

  // grid dots
  ctx.fillStyle = '#0d0d1d';
  for (let gx = 0; gx < cv.width; gx += 32)
    for (let gy = 0; gy < cv.height; gy += 32) {
      ctx.beginPath(); ctx.arc(gx, gy, 0.4, 0, Math.PI*2); ctx.fill();
    }

  drawPipeline();
  drawConnections();

  bubbles.forEach(b => { b.tick(cv.width, cv.height); b.draw(b === hovered); });
  particles = particles.filter(p => !p.done);
  particles.forEach(p => { p.tick(); p.draw(); });
  robots.forEach(r => { r.tick(); r.draw(); });

  frame++;
  PIPE.forEach(([a, b], i) => {
    const ra = robots.find(r => r.key === a); if (!ra) return;
    if (ra.status === 'active') {
      if ((frame + i*21) % 50 === 0) spark(a, b, 'data');
      if ((frame + i*43) % 135 === 0) spark(a, b, 'msg');
    } else {
      if ((frame + i*21) % 240 === 0) spark(a, b, 'data');
    }
  });
  if (frame % 92 === 0) {
    const t = ['market_scout','trend_analyst','deep_diver'];
    spark('memory', t[Math.floor(Math.random()*t.length)], 'msg');
  }
  if (frame % 165 === 0) {
    const act = robots.filter(r => r.status === 'active');
    if (act.length >= 2) {
      const a = act[Math.floor(Math.random()*act.length)];
      const rest = act.filter(r => r.key !== a.key);
      if (rest.length) spark(a.key, rest[Math.floor(Math.random()*rest.length)].key, 'msg');
    }
  }

  requestAnimationFrame(loop);
}

// ── SIDEBAR ───────────────────────────────────────────────────
function showTab(id, el) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('on'));
  el.classList.add('on');
  document.getElementById('tab-' + id).classList.add('on');
}

function renderAgents() {
  document.getElementById('tab-agents').innerHTML = agents.map(a => {
    const st = statuses[a.key];
    const s  = st ? st.status : 'unknown';
    const badge = s === 'active' ? 'ON' : s === 'rate_limited' ? 'LIMITED' : '—';
    const tasks = st?.tasks_completed || 0;
    return `<div class="acard ${s}">
      <div class="actop" onclick="toggleDet('det-${a.key}')">
        <div class="acicon" style="background:${a.color}18;color:${a.color}">${a.icon||'🤖'}</div>
        <div class="acinfo">
          <div class="acname">${a.name}</div>
          <div class="acmodel">${a.fb[0]}</div>
        </div>
        <div class="acbadge ${s}">${badge}</div>
      </div>
      <div class="acdet" id="det-${a.key}">
        ${a.fb.map(f=>`<span>${f}</span>`).join('<br>')}
        <div style="display:flex;gap:16px;margin-top:8px">
          <div><div style="font-size:8px;color:#444;letter-spacing:.05em">TASKS</div><div style="font-size:12px">${tasks}</div></div>
          <div><div style="font-size:8px;color:#444;letter-spacing:.05em">STATUS</div><div style="font-size:12px;color:${s==='active'?'#1d9e75':s==='rate_limited'?'#ba7517':'#444'}">${s}</div></div>
        </div>
      </div>
    </div>`;
  }).join('');
}

function toggleDet(id) {
  document.getElementById(id)?.classList.toggle('show');
}

function addFeed(agent, msg, color) {
  const t = new Date().toTimeString().slice(0,5);
  feedLog.unshift({agent, msg, color, t});
  if (feedLog.length > 30) feedLog.pop();
  document.getElementById('tab-feed').innerHTML = feedLog.map(f =>
    `<div class="fitem">
      <div class="fdot" style="background:${f.color}"></div>
      <div class="fbody">
        <div class="ftext"><strong>${f.agent}</strong> ${f.msg}</div>
        <div class="ftime">${f.t}</div>
      </div>
    </div>`).join('');
}

function renderInsights() {
  document.getElementById('tab-insights').innerHTML = allInsights.slice(0,15).map(i => {
    const sc = i.novelty_score || 0;
    const cls = sc >= 7 ? 'hi' : sc >= 4 ? 'mi' : 'lo';
    return `<div class="icard">
      <span class="iscore ${cls}">novelty ${sc}/10</span>
      <div class="itext">${(i.content||'').replace(/[#*]/g,'').slice(0,180)}…</div>
    </div>`;
  }).join('') || '<div style="padding:20px;font-size:10px;color:#333;text-align:center">No insights yet</div>';
}

// ── FILTER ────────────────────────────────────────────────────
function setFilter(f, btn) {
  activeFilter = f;
  document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  const d = f === 'all' ? allResults : allResults.filter(r => r.agent === f);
  seedBubbles(d);
  document.getElementById('bc').textContent = '';
  setTimeout(() => document.getElementById('bc').textContent = bubbles.length + ' bubbles', 2000);
}

// ── DOWNLOAD ──────────────────────────────────────────────────
async function downloadData() {
  try {
    const r = await fetch('/api/export');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'research_export.json'; a.click();
    URL.revokeObjectURL(url);
    addFeed('System', 'Research data exported', '#1d9e75');
  } catch(e) {
    alert('Export failed. Try visiting /api/export directly.');
  }
}

// ── ADD AGENT MODAL ───────────────────────────────────────────
function openModal() { document.getElementById('modal').classList.add('show'); }
function closeModal() { document.getElementById('modal').classList.remove('show'); }
function selC(el) {
  document.querySelectorAll('.cswatch').forEach(s => s.classList.remove('sel'));
  el.classList.add('sel'); selColor = el.dataset.c;
}
document.getElementById('modal').addEventListener('click', e => {
  if (e.target === document.getElementById('modal')) closeModal();
});

function saveAgent() {
  const name = document.getElementById('m-name').value.trim();
  const role = document.getElementById('m-role').value.trim();
  const provider = document.getElementById('m-provider').value;
  const key  = document.getElementById('m-key').value.trim();
  if (!name || !role) { alert('Please fill in name and role.'); return; }

  const provMap = {
    groq:'Groq (Llama 3.3 70B)',
    gemini:'Google Gemini 2.0 Flash',
    openrouter:'OpenRouter (Nemotron)'
  };
  const agentKey = name.toLowerCase().replace(/\s+/g,'_').replace(/[^a-z0-9_]/g,'');
  const newDef = {
    key: agentKey, name, color: selColor,
    icon: '🔬', fb: [`Primary: ${provMap[provider]}`],
    custom: true
  };
  agents.push(newDef); updateColors();

  // Add robot at a free position
  const W = cv.width, H = cv.height;
  const extraX = [W*0.22, W*0.72, W*0.05, W*0.45];
  const extraY = [H*0.75, H*0.80, H*0.55, H*0.45];
  const ci = robots.filter(r => r.custom).length;
  const nx = extraX[ci] || W * 0.5 + Math.random()*100-50;
  const ny = extraY[ci] || H * 0.5 + Math.random()*100-50;
  const rb = new Robot(newDef, nx, ny); rb.custom = true;
  robots.push(rb);

  // Add filter button
  const bar = document.getElementById('botbar');
  const btn = document.createElement('button');
  btn.className = 'fbtn';
  btn.textContent = name.slice(0,7);
  btn.onclick = function() { setFilter(agentKey, this); };
  bar.insertBefore(btn, document.getElementById('bc'));

  renderAgents();
  addFeed(name, 'added to research team! 🎉', selColor);
  closeModal();

  // Reset form
  document.getElementById('m-name').value = '';
  document.getElementById('m-role').value = '';
  document.getElementById('m-key').value  = '';
}

// ── DATA FETCH ────────────────────────────────────────────────
async function fetchStats() {
  try {
    const d = await fetch('/api/stats').then(r => r.json());
    document.getElementById('s-total').textContent = (d.total_results||0).toLocaleString();
    statuses = d.agents || {};
    robots.forEach(r => {
      const st = statuses[r.key]; if (!st) return;
      const prev = r.status; r.status = st.status || 'unknown';
      if (prev !== 'active' && r.status === 'active') addFeed(r.name, 'back online ✓', r.color);
      if (prev === 'active' && r.status === 'rate_limited') addFeed(r.name, 'rate limited → fallback', r.color);
    });
    document.getElementById('s-active').textContent =
      Object.values(statuses).filter(s => s.status==='active').length;
    renderAgents();
    const tk = document.getElementById('tick');
    tk.textContent = '● LIVE'; setTimeout(() => tk.textContent = 'LIVE', 500);
  } catch(e) {}
}

async function fetchResults() {
  try {
    const data = await fetch('/api/results').then(r => r.json());
    const prev = allResults.length;
    allResults = data;
    document.getElementById('s-topics').textContent = new Set(data.map(r=>r.topic)).size;
    if (data.length > prev && prev > 0) {
      const n = data[0];
      addBubble(n);
      const def = agents.find(a=>a.key===n.agent);
      addFeed(def?.name||n.agent, `"${(n.topic||'').slice(0,32)}"`, COL[n.agent]||'#7f77dd');
    } else if (bubbles.length < 10 && data.length > 0) {
      const d = activeFilter==='all' ? data : data.filter(r=>r.agent===activeFilter);
      seedBubbles(d);
    }
    setTimeout(() => {
      document.getElementById('bc').textContent = bubbles.length + ' bubbles';
    }, 3000);
  } catch(e) {}
}

async function fetchInsights() {
  try {
    allInsights = await fetch('/api/insights').then(r => r.json());
    renderInsights();
  } catch(e) {}
}

// ── BOOT ──────────────────────────────────────────────────────
placeRobots();
loop();
renderAgents();
fetchStats();
fetchResults();
fetchInsights();
addFeed('System', 'Hub online — click any bubble to read research', '#7f77dd');
addFeed('Manager', 'Pipeline: Scout→Analyst→Diver→Critic→Memory', '#1d9e75');
setInterval(fetchStats, 5000);
setInterval(fetchResults, 10000);
setInterval(fetchInsights, 60000);
setInterval(() => {
  document.getElementById('s-time').textContent = new Date().toTimeString().slice(0,8);
}, 1000);
setTimeout(() => {
  document.getElementById('hint').style.opacity = '0';
}, 7000);
</script>
</body>
</html>
