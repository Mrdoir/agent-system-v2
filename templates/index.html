<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Research Hub</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;600;700;800&display=swap');

*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#07070f;--bg2:#0d0d1e;--bg3:#0a0a14;--bg4:#14142a;--bg5:#1e1e3e;
  --border:#14142a;--border2:#1e1e3e;
  --txt:#ddd;--txt2:#888;--txt3:#444;--txt4:#2a2a4e;
  --pu:#7f77dd;--te:#1d9e75;--am:#ba7517;--bl:#378add;--pk:#d4537e;
  --font-mono:'Space Mono',monospace;--font-head:'Syne',sans-serif;
}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--txt);font-family:var(--font-mono);height:100vh;overflow:hidden}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:3px}::-webkit-scrollbar-thumb{background:#1a1a2e}

/* ── TOPBAR ── */
#topbar{position:fixed;top:0;left:0;right:0;height:46px;z-index:100;display:flex;align-items:center;padding:0 18px;gap:14px;background:var(--bg)ee;border-bottom:1px solid var(--border);backdrop-filter:blur(10px)}
.logo{font-family:var(--font-head);font-size:13px;font-weight:800;letter-spacing:.04em;color:#555;flex-shrink:0;white-space:nowrap}
.logo span{color:var(--pu)}
.stats-row{display:flex;gap:2px;flex:1;max-width:500px;margin:0 auto}
.stat{flex:1;text-align:center;padding:4px 6px;background:var(--bg2);border-radius:4px;border:1px solid var(--border)}
.stat-n{font-size:14px;font-weight:700;font-family:var(--font-head);line-height:1}
.pu{color:var(--pu)}.te{color:var(--te)}.am{color:var(--am)}.bl{color:var(--bl)}
.stat-l{font-size:7px;color:var(--txt3);letter-spacing:.1em;margin-top:2px}
.topbar-r{display:flex;align-items:center;gap:8px;margin-left:auto;flex-shrink:0}
.live{display:flex;align-items:center;gap:5px;font-size:9px;color:var(--te)}
.ldot{width:6px;height:6px;border-radius:50%;background:var(--te);animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.1}}
.add-btn,.dl-btn{font-size:9px;padding:5px 12px;border-radius:4px;cursor:pointer;font-family:var(--font-mono);transition:all .2s;letter-spacing:.06em;white-space:nowrap}
.add-btn{border:1px solid #7f77dd60;background:#7f77dd12;color:var(--pu)}.add-btn:hover{background:#7f77dd25}
.dl-btn{border:1px solid #1d9e7560;background:#1d9e7512;color:var(--te)}.dl-btn:hover{background:#1d9e7525}
.view-toggle{display:flex;gap:2px;background:var(--bg2);border-radius:5px;padding:2px;border:1px solid var(--border)}
.vtbtn{font-size:9px;padding:3px 10px;border-radius:3px;border:none;background:transparent;color:var(--txt3);cursor:pointer;font-family:var(--font-mono);letter-spacing:.08em;transition:all .15s}
.vtbtn.on{background:var(--bg4);color:var(--txt)}

/* ── CANVAS VIEW ── */
#c{position:fixed;top:46px;left:0;display:block}

/* ── GRAPH VIEW ── */
#graph-view{position:fixed;top:46px;left:0;bottom:30px;right:262px;display:none;background:var(--bg);overflow:hidden}
#graph-svg{width:100%;height:100%}
#graph-search-wrap{position:absolute;top:12px;left:12px;display:flex;gap:6px;align-items:center;z-index:10}
#graph-search{background:var(--bg2);border:1px solid var(--border);color:var(--txt);padding:6px 11px;border-radius:5px;font-family:var(--font-mono);font-size:10px;outline:none;width:190px;transition:border-color .2s}
#graph-search:focus{border-color:#7f77dd50}#graph-search::placeholder{color:#333}
.graph-stat{font-size:9px;color:#333;letter-spacing:.07em}
#graph-hint{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);font-size:9px;color:#2a2a4e;pointer-events:none;letter-spacing:.07em}

/* ── SIDEBAR ── */
#sb{position:fixed;right:0;top:46px;bottom:30px;width:262px;background:var(--bg2);border-left:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
.tabs{display:flex;border-bottom:1px solid var(--border);flex-shrink:0}
.tab{flex:1;padding:9px 4px;font-size:8px;letter-spacing:.1em;color:var(--txt3);cursor:pointer;text-align:center;border-bottom:2px solid transparent;transition:all .15s;font-family:var(--font-mono)}
.tab.on{color:var(--txt);border-color:var(--pu)}
.panel{display:none;flex:1;overflow-y:auto;flex-direction:column}
.panel.on{display:flex}

/* agent cards */
.acard{margin:5px 8px;border-radius:7px;border:1px solid var(--border);background:var(--bg3);overflow:hidden;transition:border-color .2s}
.acard:hover{border-color:var(--bg5)}.acard.active{border-color:#1d9e7528}.acard.rate_limited{border-color:#ba751728}
.actop{display:flex;align-items:center;gap:9px;padding:9px 10px;cursor:pointer}
.acicon{width:30px;height:30px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0}
.acinfo{flex:1;min-width:0}
.acname{font-size:11px;color:#ccc;font-family:var(--font-head);font-weight:600}
.acmodel{font-size:8px;color:var(--txt3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px}
.acbadge{font-size:8px;padding:2px 7px;border-radius:3px;flex-shrink:0;letter-spacing:.05em}
.acbadge.active{background:#0f3d2a;color:var(--te)}.acbadge.rate_limited{background:#3d2a0f;color:var(--am)}.acbadge.unknown{background:var(--bg4);color:var(--txt3)}
.acdet{border-top:1px solid var(--border);padding:9px 10px;display:none;font-size:9px;color:var(--txt3);line-height:2}
.acdet.show{display:block}.acdet span{color:var(--pu)}
.det-row{display:flex;gap:18px;margin-top:8px}
.det-col .det-lbl{font-size:7px;color:var(--txt3);letter-spacing:.08em}
.det-col .det-val{font-size:13px;font-family:var(--font-head);font-weight:700}

/* feed */
.fitem{display:flex;gap:8px;padding:8px 10px;border-bottom:1px solid #10101e}
.fdot{width:5px;height:5px;border-radius:50%;margin-top:5px;flex-shrink:0}
.fbody{flex:1;min-width:0}
.ftext{font-size:9px;color:#666;line-height:1.6}.ftext strong{color:#aaa;font-weight:normal}
.ftime{font-size:8px;color:#2a2a3e;margin-top:1px}

/* insights */
.icard{margin:6px 8px;border-radius:7px;border:1px solid var(--border);background:var(--bg3);padding:10px;cursor:pointer;transition:border-color .2s}
.icard:hover{border-color:var(--bg5)}
.iscore{font-size:8px;padding:2px 7px;border-radius:3px;display:inline-block;margin-bottom:6px;letter-spacing:.05em}
.itext{font-size:9px;color:#666;line-height:1.7}
.iscore.hi{background:#0f3d2a;color:var(--te)}.iscore.mi{background:#3d2a0f;color:var(--am)}.iscore.lo{background:var(--bg4);color:var(--txt3)}

/* ── BOTBAR ── */
#botbar{position:fixed;bottom:0;left:0;right:262px;height:30px;z-index:100;display:flex;align-items:center;padding:0 14px;gap:5px;background:var(--bg)ee;border-top:1px solid var(--border);backdrop-filter:blur(10px)}
.fl{font-size:8px;color:var(--txt3);letter-spacing:.1em;margin-right:3px}
.fbtn{font-size:8px;padding:3px 10px;border-radius:3px;border:1px solid var(--border);background:transparent;color:var(--txt3);cursor:pointer;font-family:var(--font-mono);transition:all .15s;letter-spacing:.04em}
.fbtn.on{background:var(--bg4);color:var(--txt);border-color:var(--bg5)}
#bc{margin-left:auto;font-size:8px;color:#333}

/* ── POPUP ── */
#popup{position:fixed;z-index:500;background:var(--bg2);border:1px solid var(--bg5);border-radius:14px;width:510px;max-height:78vh;box-shadow:0 30px 80px #000000c0;display:none;flex-direction:column;opacity:0;transform:translateY(10px) scale(.97);transition:opacity .22s,transform .22s}
#popup.show{opacity:1;transform:none}
.ph{padding:18px 20px 14px;border-bottom:1px solid var(--border);flex-shrink:0}
.ptop{display:flex;justify-content:space-between;align-items:flex-start;gap:14px}
.pagent{font-size:9px;padding:3px 10px;border-radius:99px;display:inline-block;margin-bottom:9px;border:1px solid;letter-spacing:.05em}
.ptopic{font-size:14px;color:var(--txt);line-height:1.4;font-family:var(--font-head);font-weight:700}
.pmeta{font-size:9px;color:var(--txt3);margin-top:6px;display:flex;align-items:center;gap:10px}
.pscore{font-size:9px;padding:2px 8px;border-radius:3px}
.pscore.hi{background:#0f3d2a;color:var(--te)}.pscore.mi{background:#3d2a0f;color:var(--am)}.pscore.lo{background:var(--bg4);color:var(--txt3)}
.pclose{background:none;border:1px solid var(--border);color:#555;padding:5px 13px;border-radius:6px;cursor:pointer;font-family:var(--font-mono);font-size:10px;transition:all .15s;flex-shrink:0}
.pclose:hover{color:var(--txt);border-color:var(--bg5);background:var(--bg4)}
.pbody{padding:16px 20px;overflow-y:auto;flex:1}
.pcontent{font-size:11px;color:#777;line-height:2;white-space:pre-wrap}
.ptags{display:flex;flex-wrap:wrap;gap:5px;margin-top:12px}
.ptag{font-size:8px;padding:2px 8px;border-radius:3px;border:1px solid var(--bg5);color:#555;letter-spacing:.04em}

/* ── ADD AGENT MODAL ── */
.moverlay{position:fixed;inset:0;z-index:600;background:#00000095;backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center}
.moverlay.show{display:flex}
.modal{background:var(--bg2);border:1px solid var(--bg5);border-radius:16px;padding:30px;width:490px;box-shadow:0 40px 100px #000000c0;max-height:90vh;overflow-y:auto}
.mtitle{font-family:var(--font-head);font-size:16px;font-weight:800;color:var(--txt);margin-bottom:6px}
.msub{font-size:9px;color:#555;margin-bottom:24px;line-height:1.8}
.field{margin-bottom:15px}
.field label{display:block;font-size:8px;color:#555;letter-spacing:.1em;margin-bottom:6px}
.field input,.field select,.field textarea{width:100%;background:var(--bg);border:1px solid var(--bg5);color:var(--txt);padding:10px 13px;border-radius:7px;font-family:var(--font-mono);font-size:11px;outline:none;transition:border-color .2s}
.field input:focus,.field select:focus,.field textarea:focus{border-color:#7f77dd55}
.field textarea{resize:vertical;min-height:68px}
.field select option{background:var(--bg2)}
.color-row{display:flex;gap:9px;flex-wrap:wrap}
.cswatch{width:26px;height:26px;border-radius:50%;cursor:pointer;border:2px solid transparent;transition:all .15s}
.cswatch.sel{border-color:#fff;transform:scale(1.15)}
.mbtns{display:flex;gap:10px;justify-content:flex-end;margin-top:24px}
.mcancel{background:none;border:1px solid var(--bg5);color:#666;padding:9px 20px;border-radius:7px;cursor:pointer;font-family:var(--font-mono);font-size:10px;transition:all .15s}
.mcancel:hover{color:var(--txt);border-color:var(--txt3)}
.msave{background:#7f77dd18;border:1px solid #7f77dd55;color:var(--pu);padding:9px 20px;border-radius:7px;cursor:pointer;font-family:var(--font-mono);font-size:10px;transition:all .15s}
.msave:hover{background:#7f77dd30}

/* ── HINT ── */
#hint{position:fixed;bottom:38px;left:50%;transform:translateX(-50%);font-size:9px;color:#2a2a4e;pointer-events:none;letter-spacing:.08em;transition:opacity 2s;z-index:50;white-space:nowrap}

/* ── LOADING ── */
#loader{position:fixed;inset:0;background:var(--bg);z-index:999;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;transition:opacity .6s}
#loader.hide{opacity:0;pointer-events:none}
.load-logo{font-family:var(--font-head);font-size:28px;font-weight:800;color:var(--pu);letter-spacing:.05em}
.load-bar{width:220px;height:2px;background:var(--bg4);border-radius:99px;overflow:hidden}
.load-fill{height:100%;background:linear-gradient(90deg,var(--pu),var(--bl));width:0;transition:width 1s;border-radius:99px}
.load-sub{font-size:9px;color:#333;letter-spacing:.1em}
</style>
</head>
<body>

<!-- LOADING SCREEN -->
<div id="loader">
  <div class="load-logo">AGENT HUB</div>
  <div class="load-bar"><div class="load-fill" id="load-fill"></div></div>
  <div class="load-sub" id="load-sub">INITIALIZING AGENTS…</div>
</div>

<!-- TOPBAR -->
<div id="topbar">
  <div class="logo">// <span>AGENT</span> RESEARCH HUB</div>
  <div class="stats-row">
    <div class="stat"><div class="stat-n pu" id="s-total">0</div><div class="stat-l">RESULTS</div></div>
    <div class="stat"><div class="stat-n te" id="s-active">0</div><div class="stat-l">ACTIVE</div></div>
    <div class="stat"><div class="stat-n am" id="s-topics">0</div><div class="stat-l">TOPICS</div></div>
    <div class="stat"><div class="stat-n bl" id="s-time">--:--:--</div><div class="stat-l">CLOCK</div></div>
  </div>
  <div class="topbar-r">
    <div class="view-toggle">
      <button class="vtbtn on" id="btn-canvas" onclick="setView('canvas')">⬡ ROBOTS</button>
      <button class="vtbtn" id="btn-graph" onclick="setView('graph')">◈ GRAPH</button>
    </div>
    <div class="live"><div class="ldot"></div><span id="tick">LIVE</span></div>
    <button class="dl-btn" onclick="exportData()">↓ EXPORT</button>
    <button class="add-btn" onclick="openModal()">+ ADD AGENT</button>
  </div>
</div>

<!-- CANVAS -->
<canvas id="c"></canvas>

<!-- GRAPH VIEW -->
<div id="graph-view">
  <div id="graph-search-wrap">
    <input id="graph-search" type="text" placeholder="search nodes…" oninput="graphSearch(this.value)">
    <span class="graph-stat" id="graph-node-count"></span>
  </div>
  <svg id="graph-svg"></svg>
  <div id="graph-hint">drag nodes · scroll to zoom · click bubble to read</div>
</div>

<!-- SIDEBAR -->
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

<!-- BOTBAR -->
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

<!-- POPUP -->
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
  <div class="pbody">
    <div class="pcontent" id="p-content"></div>
    <div class="ptags" id="p-tags"></div>
  </div>
</div>

<!-- ADD AGENT MODAL -->
<div class="moverlay" id="modal">
  <div class="modal">
    <div class="mtitle">Add New Research Agent</div>
    <div class="msub">Configure a new AI agent for your research pipeline. Give it a name, a role, pick a provider, and paste your API key.</div>
    <div class="field"><label>AGENT NAME</label><input id="m-name" placeholder="e.g. Competitor Analyst" maxlength="30"></div>
    <div class="field"><label>RESEARCH FOCUS</label><textarea id="m-role" placeholder="e.g. Finds direct competitors, analyzes pricing gaps and weaknesses"></textarea></div>
    <div class="field"><label>AI PROVIDER</label>
      <select id="m-provider">
        <option value="groq">Groq — Llama 3.3 70B (free tier)</option>
        <option value="gemini">Google Gemini 2.0 Flash (free tier)</option>
        <option value="openrouter">OpenRouter — Nemotron (free tier)</option>
        <option value="anthropic">Anthropic — Claude Sonnet</option>
      </select>
    </div>
    <div class="field"><label>API KEY</label><input id="m-key" type="password" placeholder="Paste your API key here"></div>
    <div class="field"><label>AGENT COLOR</label>
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
// ═══════════════════════════════════════════════
// SIMULATED DATA (replace with real API calls)
// ═══════════════════════════════════════════════
const FAKE_TOPICS = [
  'AI productivity tools 2024','No-code platform wars','Remote work software gaps',
  'Developer tooling trends','B2B SaaS pricing shifts','Open-source AI momentum',
  'Edge computing growth','API economy expansion','LLM fine-tuning market',
  'Data privacy regulations','Vertical AI applications','Autonomous agent frameworks',
  'Vector database adoption','Multimodal AI tools','Observability platform gaps'
];
const FAKE_CONTENT = [
  `The market for AI productivity tools has seen explosive growth this quarter. Key findings:\n\n• Cursor AI surpassed 100k paid users with minimal marketing spend\n• Notion AI integrations up 340% YoY — but retention below 60%\n• Clear gap: real-time collaboration with AI in specialized domains (legal, medical)\n• Opportunity: vertical-specific tooling with deep workflow integrations\n\nRecommendation: Target niche verticals where horizontal tools underperform. Legal and healthcare represent $2.4B underserved.`,
  `Trend analysis reveals accelerating consolidation in no-code platforms. Bubble and Webflow are eating the long tail while Framer takes design-led market.\n\nCritical insight: The gap is in AI-native no-code for internal tools. Retool dominates but leaves $800M+ annual contract value on table from SMBs who find it too complex.\n\nWeakness vector: None of the top 5 players have strong mobile-native workflows.`,
  `Deep research into developer tooling shows GitHub Copilot fatigue setting in. 38% of surveyed developers using 2+ AI coding tools simultaneously.\n\nKey finding: The "context problem" — AI tools lose track of large codebases. Teams spending 3-5 hours/week on AI context management.\n\nEmerging winners: Tools that maintain persistent project context (Cursor, Aider) vs stateless completions (Copilot).`,
  `B2B SaaS pricing models are undergoing structural shift. Usage-based pricing adoption up 62% but customer acquisition costs rising 28%.\n\nCritical: The hybrid seat+usage model is winning. Companies like Snowflake and Datadog show 140% net revenue retention with hybrid.\n\nOpportunity: Verticalized pricing calculators and cost prediction tools have near-zero competition.`,
  `Open source AI momentum is creating compression at the foundation model layer. Llama 3.3 70B performance within 15% of GPT-4o on most enterprise benchmarks.\n\nImplication: Value migrating to fine-tuning, deployment infrastructure, and domain-specific datasets.\n\nWinners emerging: Companies owning proprietary datasets in regulated industries (finance, legal, healthcare).`
];
const FAKE_TAGS = [
  ['market-gap','b2b','saas','ai-tools'],['competitive-analysis','no-code','platform'],
  ['developer-tools','adoption','trends'],['pricing','revenue-model','b2b'],
  ['open-source','llm','infrastructure'],['vertical-ai','healthcare','regulation'],
  ['productivity','workflow','automation'],['data','privacy','compliance']
];

// Generate fake results
let allResults = [];
let idCounter = 1;
const AGENT_KEYS = ['market_scout','trend_analyst','deep_diver','critic','memory'];
function generateResult(agentKey) {
  const topicIdx = Math.floor(Math.random()*FAKE_TOPICS.length);
  return {
    id: idCounter++,
    agent: agentKey || AGENT_KEYS[Math.floor(Math.random()*AGENT_KEYS.length)],
    topic: FAKE_TOPICS[topicIdx],
    content: FAKE_CONTENT[Math.floor(Math.random()*FAKE_CONTENT.length)],
    score: 3 + Math.floor(Math.random()*8),
    tags: FAKE_TAGS[Math.floor(Math.random()*FAKE_TAGS.length)],
    created_at: new Date(Date.now() - Math.random()*86400000*7).toISOString()
  };
}

// Seed initial data
for(let i=0;i<35;i++) allResults.push(generateResult());
allResults.sort((a,b)=>new Date(b.created_at)-new Date(a.created_at));

let allInsights = [
  {novelty_score:9,content:'# Key Insight\nNo current tool addresses AI-assisted legal document drafting with jurisdiction-aware context. Estimated TAM $1.2B with zero dominant players. Window: 18 months before BigLaw builds in-house.'},
  {novelty_score:8,content:'# Emerging Pattern\nDeveloper tooling fatigue is creating demand for "AI orchestrators" — single interfaces that route to the right AI tool contextually. No product does this well yet.'},
  {novelty_score:7,content:'# Market Signal\nVertical SaaS with embedded AI is showing 3x faster growth than horizontal AI layers. Specialization premium is real and growing.'},
  {novelty_score:6,content:'# Pricing Insight\nHybrid seat+usage pricing shows 140% NRR vs 108% for pure seat. The shift is structural, not cyclical. Recommend repositioning pricing model.'},
  {novelty_score:5,content:'# Competitive Intel\nOpen source LLM quality convergence means differentiation is moving to: (1) fine-tuning expertise, (2) proprietary data, (3) deployment tooling. Act now.'},
];

// ═══════════════════════════════════════════════
// AGENT DEFINITIONS
// ═══════════════════════════════════════════════
const AGENTS_DEF = [
  {key:'market_scout',  name:'Scout',   color:'#378add', icon:'🔍', fb:['Primary: Gemini 2.0 Flash','→ Fallback: Groq Llama 3.3']},
  {key:'trend_analyst', name:'Analyst', color:'#1d9e75', icon:'📈', fb:['Primary: Groq Llama 3.3','→ Fallback: Gemini Flash']},
  {key:'deep_diver',    name:'Diver',   color:'#7f77dd', icon:'🧠', fb:['Primary: Nemotron (OpenRouter)','→ Fallback 1: QwQ','→ Fallback 2: Gemini']},
  {key:'critic',        name:'Critic',  color:'#d85a30', icon:'⚡', fb:['Primary: Groq Llama 3.3','→ Validates all findings']},
  {key:'memory',        name:'Memory',  color:'#ba7517', icon:'💾', fb:['Primary: Gemini 2.0 Flash','→ Long-term storage & recall']},
  {key:'synthesis',     name:'Synth',   color:'#d4537e', icon:'✨', fb:['Weekly synthesis run','→ Every Sunday 09:00']},
];

let agents = [...AGENTS_DEF];
const COL = {};
const updateColors = () => agents.forEach(a => COL[a.key] = a.color);
updateColors();

// Simulated statuses
let statuses = {};
agents.forEach((a,i) => {
  statuses[a.key] = {
    status: i < 4 ? 'active' : (i===4?'rate_limited':'unknown'),
    tasks_completed: Math.floor(Math.random()*80)+10
  };
});

// ═══════════════════════════════════════════════
// CANVAS + ROBOTS
// ═══════════════════════════════════════════════
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
function resizeCanvas(){cv.width=window.innerWidth-262;cv.height=window.innerHeight-46-30;}
resizeCanvas();
window.addEventListener('resize',()=>{resizeCanvas();placeRobots();if(currentView==='graph')buildGraph(filteredResults());});

let bubbles=[],robots=[],particles=[],frame=0,hovered=null;
let activeFilter='all',selColor='#7f77dd';
let currentView='canvas',loopRunning=true;
let graphSimulation=null,graphSearchTerm='';
let feedLog=[];

// ─── Robot ───
class Robot {
  constructor(def,x,y){
    this.key=def.key;this.name=def.name;this.color=def.color;this.icon=def.icon||'🤖';
    this.x=x;this.y=y;this.tx=x;this.ty=y;this.status='unknown';
    this.p=Math.random()*Math.PI*2;this.w=Math.random()*Math.PI*2;
    this.custom=false;
  }
  tick(){
    this.p+=0.028;this.w+=0.015;
    this.x+=(this.tx-this.x)*0.05;this.y+=(this.ty-this.y)*0.05;
    const st=statuses[this.key];if(st)this.status=st.status||'unknown';
  }
  draw(){
    const{x,y,color:c,status:s,p,w,name}=this;
    const active=s==='active',lim=s==='rate_limited';
    const bob=active?Math.sin(w)*2.8:0,wy=y+bob;
    const glow=active?0.6+0.28*Math.sin(p):0.18;
    ctx.save();
    ctx.globalAlpha=lim?0.32:1;
    // halo glow
    if(active){
      ctx.globalAlpha=0.06+0.04*Math.sin(p);ctx.fillStyle=c;
      ctx.beginPath();ctx.arc(x,wy,56,0,Math.PI*2);ctx.fill();
      ctx.globalAlpha=0.03+0.02*Math.sin(p*1.3);
      ctx.beginPath();ctx.arc(x,wy,76,0,Math.PI*2);ctx.fill();
      ctx.globalAlpha=lim?0.32:1;
    }
    // platform shadow
    ctx.globalAlpha=(lim?0.32:1)*0.6;
    ctx.fillStyle='#00000060';
    ctx.beginPath();ctx.ellipse(x,wy+34,28,5,0,0,Math.PI*2);ctx.fill();
    ctx.globalAlpha=lim?0.32:1;
    // platform
    ctx.fillStyle='#0c0c1e';ctx.strokeStyle=c+'30';ctx.lineWidth=1;
    ctx.beginPath();ctx.roundRect(x-34,wy+26,68,9,3);ctx.fill();ctx.stroke();
    // legs
    ctx.globalAlpha=(lim?0.32:1)*(active?0.75:0.18);ctx.strokeStyle=c;ctx.lineWidth=2.2;ctx.lineCap='round';
    const sw=active?Math.sin(p*2)*4:0;
    ctx.beginPath();ctx.moveTo(x-5,wy+12);ctx.lineTo(x-5-sw,wy+26);ctx.stroke();
    ctx.beginPath();ctx.moveTo(x+5,wy+12);ctx.lineTo(x+5+sw,wy+26);ctx.stroke();
    ctx.globalAlpha=lim?0.32:1;
    // body
    ctx.fillStyle='#0a0a1c';ctx.strokeStyle=c;ctx.lineWidth=1.5;
    ctx.beginPath();ctx.roundRect(x-14,wy-13,28,26,6);ctx.fill();ctx.stroke();
    // chest detail
    if(active){
      ctx.globalAlpha=(lim?0.32:1)*0.3;ctx.fillStyle=c;
      ctx.beginPath();ctx.roundRect(x-5,wy-2,10,7,2);ctx.fill();
    }
    ctx.globalAlpha=lim?0.32:1;
    // head
    ctx.fillStyle='#0a0a1c';ctx.strokeStyle=c;ctx.lineWidth=1.5;
    ctx.beginPath();ctx.roundRect(x-11,wy-27,22,16,5);ctx.fill();ctx.stroke();
    // antenna
    if(active){
      ctx.globalAlpha=(lim?0.32:1)*(0.55+0.3*Math.sin(p*1.6));
      ctx.strokeStyle=c;ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(x,wy-27);ctx.lineTo(x,wy-37);ctx.stroke();
      ctx.fillStyle=c;ctx.beginPath();ctx.arc(x,wy-39,3.2,0,Math.PI*2);ctx.fill();
      ctx.globalAlpha=(lim?0.32:1)*0.12;ctx.beginPath();ctx.arc(x,wy-39,8,0,Math.PI*2);ctx.fill();
      ctx.globalAlpha=lim?0.32:1;
    }
    // eyes
    ctx.globalAlpha=(lim?0.32:1)*glow;ctx.fillStyle=c;ctx.shadowColor=c;ctx.shadowBlur=active?8:0;
    ctx.beginPath();ctx.arc(x-3.8,wy-20,2.4,0,Math.PI*2);ctx.fill();
    ctx.beginPath();ctx.arc(x+3.8,wy-20,2.4,0,Math.PI*2);ctx.fill();
    ctx.shadowBlur=0;
    // arms
    ctx.globalAlpha=(lim?0.32:1)*(active?0.75:0.15);
    const aw=active?Math.sin(p*2+1)*6:0;
    ctx.strokeStyle=c;ctx.lineWidth=2.2;
    ctx.beginPath();ctx.moveTo(x-14,wy-2);ctx.lineTo(x-22-aw,wy+5);ctx.stroke();
    ctx.beginPath();ctx.moveTo(x+14,wy-2);ctx.lineTo(x+22+aw,wy+5);ctx.stroke();
    // status dot
    ctx.globalAlpha=lim?0.32:1;
    ctx.fillStyle=active?'#1d9e75':lim?'#ba7517':'#1a1a2e';
    ctx.shadowColor=active?'#1d9e75':'transparent';ctx.shadowBlur=active?7:0;
    ctx.beginPath();ctx.arc(x+10,wy-5,3,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
    // status label
    ctx.globalAlpha=(lim?0.32:1)*0.7;
    ctx.fillStyle=active?'#1d9e75':lim?'#ba7517':'#2a2a3e';
    ctx.font='7px Space Mono,Courier New';ctx.textAlign='center';
    ctx.fillText(active?'● LIVE':lim?'⚠ LIMITED':'○ OFFLINE',x,wy+40);
    // name
    ctx.globalAlpha=(lim?0.32:1)*0.45;ctx.fillStyle='#777';
    ctx.font='8px Syne,sans-serif';
    ctx.fillText(name,x,wy+51);
    ctx.restore();
  }
}

function placeRobots(){
  const W=cv.width,H=cv.height;
  const slots=[
    {key:'market_scout',  x:W*0.12,y:H*0.27},{key:'trend_analyst',x:W*0.34,y:H*0.62},
    {key:'deep_diver',    x:W*0.58,y:H*0.23},{key:'critic',       x:W*0.80,y:H*0.54},
    {key:'memory',        x:W*0.91,y:H*0.22},{key:'synthesis',    x:W*0.50,y:H*0.80},
  ];
  const extras=[{x:W*0.22,y:H*0.76},{x:W*0.71,y:H*0.80},{x:W*0.06,y:H*0.56},{x:W*0.44,y:H*0.44}];
  let ei=0;
  if(robots.length===0){
    robots=agents.map(d=>{
      const slot=slots.find(s=>s.key===d.key)||extras[ei++]||{x:W*0.5,y:H*0.5};
      return new Robot(d,slot.x,slot.y);
    });
  }else{
    robots.forEach(r=>{
      const slot=slots.find(s=>s.key===r.key)||extras[ei++];
      if(slot){r.tx=slot.x;r.ty=slot.y;}
    });
  }
}

// ─── Bubble ───
class Bubble{
  constructor(res,x,y){
    this.res=res;this.x=x;this.y=y;
    this.vx=(Math.random()-0.5)*0.18;this.vy=(Math.random()-0.5)*0.18;
    this.color=COL[res.agent]||'#2a2a6e';this.p=Math.random()*Math.PI*2;
    this.age=0;this.rad=7+Math.min(13,(res.score||0)*1.4);this.conn=[];
    this.label=(res.topic||'').slice(0,22);
  }
  tick(W,H){
    this.p+=0.019;this.age++;this.x+=this.vx;this.y+=this.vy;
    if(this.x<18)this.vx+=0.06;if(this.x>W-18)this.vx-=0.06;
    if(this.y<12)this.vy+=0.06;if(this.y>H-12)this.vy-=0.06;
    this.vx*=0.997;this.vy*=0.997;
  }
  draw(hov){
    const{x,y,rad:r,color:c,p,age,label}=this;
    const fi=Math.min(1,age/45),g=hov?1:0.38+0.14*Math.sin(p);
    ctx.save();
    // outer halo
    ctx.globalAlpha=fi*g*0.08;ctx.fillStyle=c;ctx.beginPath();ctx.arc(x,y,r+14,0,Math.PI*2);ctx.fill();
    ctx.globalAlpha=fi*g*0.05;ctx.beginPath();ctx.arc(x,y,r+8,0,Math.PI*2);ctx.fill();
    // bubble
    ctx.globalAlpha=fi*(hov?0.9:0.48);
    ctx.fillStyle=c+'15';ctx.strokeStyle=c+(hov?'cc':'50');ctx.lineWidth=hov?1.8:0.9;
    ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.stroke();
    // core dot
    ctx.globalAlpha=fi*(hov?1:g*0.85);ctx.fillStyle=c;ctx.shadowColor=c;ctx.shadowBlur=hov?12:5;
    ctx.beginPath();ctx.arc(x,y,r*0.2,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
    // ring on hover
    if(hov){
      ctx.globalAlpha=0.18+0.14*Math.sin(p*3);ctx.strokeStyle=c;ctx.lineWidth=1.2;
      ctx.beginPath();ctx.arc(x,y,r+20,0,Math.PI*2);ctx.stroke();
      ctx.globalAlpha=0.1+0.08*Math.sin(p*2.1);
      ctx.beginPath();ctx.arc(x,y,r+30,0,Math.PI*2);ctx.stroke();
    }
    // label
    if(hov||r>11){
      const lw=Math.min(label.length*5.2+16,130);
      ctx.globalAlpha=fi*(hov?1:0.82);ctx.shadowBlur=0;
      ctx.fillStyle='#07070f';ctx.strokeStyle=c+(hov?'70':'30');ctx.lineWidth=0.6;
      ctx.beginPath();ctx.roundRect(x-lw/2,y+r+5,lw,15,4);ctx.fill();ctx.stroke();
      ctx.fillStyle=hov?c:c+'cc';ctx.font=(hov?'8.5':'7.5')+'px Space Mono,Courier New';
      ctx.textAlign='center';ctx.fillText(label.slice(0,20),x,y+r+15);
    }
    ctx.restore();
  }
  hit(mx,my){const dx=mx-this.x,dy=my-this.y;return Math.sqrt(dx*dx+dy*dy)<=this.rad+12;}
}

function addBubble(res){
  const W=cv.width,H=cv.height;
  const rb=robots.find(r=>r.key===res.agent);
  let x,y;
  if(rb){x=rb.x+(Math.random()-0.5)*170;y=rb.y+(Math.random()-0.5)*150;}
  else{x=40+Math.random()*(W-80);y=20+Math.random()*(H-40);}
  x=Math.max(18,Math.min(W-18,x));y=Math.max(12,Math.min(H-12,y));
  const b=new Bubble(res,x,y);
  // cluster connections
  bubbles.filter(e=>e.res.agent===res.agent).slice(-8).forEach(e=>{
    const dx=e.x-x,dy=e.y-y;
    if(Math.sqrt(dx*dx+dy*dy)<190&&b.conn.length<2)b.conn.push({node:e,type:'cluster'});
  });
  bubbles.filter(e=>e.res.agent!==res.agent&&e.res.topic===res.topic).forEach(e=>{
    if(b.conn.length<5)b.conn.push({node:e,type:'relevant'});
  });
  bubbles.push(b);
  if(bubbles.length>150)bubbles.shift();
}

function seedBubbles(data){
  bubbles=[];
  const byAgent={};
  data.forEach(r=>{if(!byAgent[r.agent])byAgent[r.agent]=[];byAgent[r.agent].push(r);});
  let seeded=[];
  Object.values(byAgent).forEach(g=>seeded.push(...g.slice(0,22)));
  seeded.sort(()=>Math.random()-0.5);
  seeded.forEach((r,i)=>setTimeout(()=>addBubble(r),i*16));
}

// ─── Particles ───
class Particle{
  constructor(x,y,tx,ty,c,type){
    this.x=x;this.y=y;this.sx=x;this.sy=y;this.tx=tx;this.ty=ty;
    this.c=c;this.type=type||'data';
    this.p=0;this.spd=0.007+Math.random()*0.005;this.done=false;
    this.sz=type==='msg'?4:1.6+Math.random()*1.3;this.trail=[];
  }
  tick(){
    this.p+=this.spd;if(this.p>=1){this.done=true;return;}
    const t=this.p,arc=this.type==='msg'?75:48;
    const nx=this.sx+(this.tx-this.sx)*t;
    const ny=this.sy+(this.ty-this.sy)*t-Math.sin(t*Math.PI)*arc;
    if(this.type==='msg')this.trail.push({x:nx,y:ny});
    if(this.trail.length>10)this.trail.shift();
    this.x=nx;this.y=ny;
  }
  draw(){
    ctx.save();
    if(this.type==='msg'){
      this.trail.forEach((tr,i)=>{ctx.globalAlpha=(i/this.trail.length)*0.2*(1-this.p);ctx.fillStyle=this.c;ctx.beginPath();ctx.arc(tr.x,tr.y,this.sz*0.4,0,Math.PI*2);ctx.fill();});
      ctx.globalAlpha=(1-this.p)*0.85;ctx.fillStyle=this.c+'18';ctx.strokeStyle=this.c;ctx.lineWidth=1.1;
      ctx.beginPath();ctx.roundRect(this.x-4.5,this.y-3.5,9,7,2);ctx.fill();ctx.stroke();
      ctx.fillStyle=this.c;ctx.globalAlpha=(1-this.p);ctx.beginPath();ctx.arc(this.x,this.y,1.4,0,Math.PI*2);ctx.fill();
    }else{
      ctx.globalAlpha=(1-this.p)*0.8;ctx.fillStyle=this.c;ctx.shadowColor=this.c;ctx.shadowBlur=4;
      ctx.beginPath();ctx.arc(this.x,this.y,this.sz,0,Math.PI*2);ctx.fill();
    }
    ctx.restore();
  }
}

function spark(fk,tk,type){
  const f=robots.find(r=>r.key===fk),t=robots.find(r=>r.key===tk);
  if(f&&t)particles.push(new Particle(f.x,f.y,t.x,t.y,COL[fk]||f.color,type||'data'));
}

const PIPE=[['market_scout','trend_analyst'],['trend_analyst','deep_diver'],
  ['deep_diver','critic'],['critic','memory'],['critic','synthesis'],['memory','market_scout']];

function drawPipeline(){
  PIPE.forEach(([a,b])=>{
    const ra=robots.find(r=>r.key===a),rb=robots.find(r=>r.key===b);if(!ra||!rb)return;
    ctx.save();ctx.strokeStyle=ra.status==='active'?COL[a]+'20':'#11112a';
    ctx.lineWidth=ra.status==='active'?1:0.5;ctx.setLineDash([3,13]);
    ctx.beginPath();ctx.moveTo(ra.x,ra.y);ctx.lineTo(rb.x,rb.y);ctx.stroke();
    ctx.setLineDash([]);ctx.restore();
  });
}

function drawConnections(){
  bubbles.forEach(b=>{
    b.conn.forEach(({node:o,type})=>{
      if(!bubbles.includes(o))return;
      ctx.save();
      if(type==='relevant'){
        ctx.strokeStyle=b.color+'50';ctx.lineWidth=0.8;ctx.setLineDash([1,5]);
        ctx.beginPath();ctx.moveTo(b.x,b.y);ctx.lineTo(o.x,o.y);ctx.stroke();
        ctx.setLineDash([]);ctx.globalAlpha=0.4;ctx.fillStyle=b.color;
        ctx.beginPath();ctx.arc((b.x+o.x)/2,(b.y+o.y)/2,1.8,0,Math.PI*2);ctx.fill();
      }else{
        ctx.strokeStyle=b.color+'12';ctx.lineWidth=0.35;ctx.setLineDash([2,10]);
        ctx.beginPath();ctx.moveTo(b.x,b.y);ctx.lineTo(o.x,o.y);ctx.stroke();
      }
      ctx.restore();
    });
  });
}

// ─── Mouse ───
let mx=-999,my=-999;
cv.addEventListener('mousemove',e=>{
  const r=cv.getBoundingClientRect();mx=e.clientX-r.left;my=e.clientY-r.top;
  hovered=[...bubbles].reverse().find(b=>b.hit(mx,my))||null;
  cv.style.cursor=hovered?'pointer':'default';
});
cv.addEventListener('click',e=>{
  const r=cv.getBoundingClientRect();
  const hit=[...bubbles].reverse().find(b=>b.hit(e.clientX-r.left,e.clientY-r.top));
  if(hit){openPopup(hit.res,e.clientX,e.clientY);document.getElementById('hint').style.opacity='0';}
});

// ─── Main Loop ───
function loop(){
  if(!loopRunning)return;
  ctx.clearRect(0,0,cv.width,cv.height);
  // dot grid bg
  ctx.fillStyle='#0d0d1d';
  for(let gx=0;gx<cv.width;gx+=32)for(let gy=0;gy<cv.height;gy+=32){ctx.beginPath();ctx.arc(gx,gy,0.4,0,Math.PI*2);ctx.fill();}
  drawPipeline();drawConnections();
  bubbles.forEach(b=>{b.tick(cv.width,cv.height);b.draw(b===hovered);});
  particles=particles.filter(p=>!p.done);
  particles.forEach(p=>{p.tick();p.draw();});
  robots.forEach(r=>{r.tick();r.draw();});
  frame++;
  PIPE.forEach(([a,b],i)=>{
    const ra=robots.find(r=>r.key===a);if(!ra)return;
    if(ra.status==='active'){if((frame+i*22)%52===0)spark(a,b,'data');if((frame+i*44)%138===0)spark(a,b,'msg');}
    else{if((frame+i*22)%250===0)spark(a,b,'data');}
  });
  if(frame%95===0){const t=['market_scout','trend_analyst','deep_diver'];spark('memory',t[Math.floor(Math.random()*t.length)],'msg');}
  if(frame%170===0){
    const act=robots.filter(r=>r.status==='active');if(act.length>=2){
      const a=act[Math.floor(Math.random()*act.length)];
      const rest=act.filter(r=>r.key!==a.key);
      if(rest.length)spark(a.key,rest[Math.floor(Math.random()*rest.length)].key,'msg');
    }
  }
  requestAnimationFrame(loop);
}

// ═══════════════════════════════════════════════
// GRAPH (D3)
// ═══════════════════════════════════════════════
function filteredResults(){return activeFilter==='all'?allResults:allResults.filter(r=>r.agent===activeFilter);}

function buildGraph(data){
  const svgEl=document.getElementById('graph-svg');
  const W=svgEl.clientWidth||(window.innerWidth-262);
  const H=svgEl.clientHeight||(window.innerHeight-46-30);
  d3.select('#graph-svg').selectAll('*').remove();
  if(graphSimulation){graphSimulation.stop();graphSimulation=null;}
  if(!data||data.length===0){
    d3.select('#graph-svg').append('text').attr('x',W/2).attr('y',H/2)
      .attr('text-anchor','middle').attr('fill','#2a2a3e')
      .attr('font-family','Space Mono, Courier New').attr('font-size','12px')
      .text('No research data — agents initializing');return;
  }
  const filtered=graphSearchTerm
    ?data.filter(r=>(r.topic||'').toLowerCase().includes(graphSearchTerm)||(r.content||'').toLowerCase().includes(graphSearchTerm)||(r.agent||'').toLowerCase().includes(graphSearchTerm))
    :data;
  document.getElementById('graph-node-count').textContent=filtered.length+' nodes';
  const topicMap={};
  filtered.forEach(r=>{if(!topicMap[r.topic])topicMap[r.topic]=[];topicMap[r.topic].push(r);});
  const nodes=[],links=[];
  Object.keys(topicMap).forEach(topic=>{nodes.push({id:'topic__'+topic,type:'topic',label:topic.slice(0,24),color:'#ffffff',r:13,data:null});});
  filtered.forEach((r,i)=>{
    const id='res__'+(r.id||i);
    nodes.push({id,type:'result',label:(r.topic||'').slice(0,18),color:COL[r.agent]||'#7f77dd',r:6+Math.min(8,(r.score||0)),data:r});
    links.push({source:id,target:'topic__'+r.topic,type:'topic'});
  });
  const byAgent={};
  filtered.forEach((r,i)=>{if(!byAgent[r.agent])byAgent[r.agent]=[];byAgent[r.agent].push('res__'+(r.id||i));});
  Object.values(byAgent).forEach(ids=>{for(let i=0;i<ids.length-1;i++)links.push({source:ids[i],target:ids[i+1],type:'agent'});});
  const svg=d3.select('#graph-svg');
  const defs=svg.append('defs');
  const gf=defs.append('filter').attr('id','glow');
  gf.append('feGaussianBlur').attr('stdDeviation','3').attr('result','blur');
  const gm=gf.append('feMerge');gm.append('feMergeNode').attr('in','blur');gm.append('feMergeNode').attr('in','SourceGraphic');
  const gf2=defs.append('filter').attr('id','glow2');
  gf2.append('feGaussianBlur').attr('stdDeviation','7').attr('result','blur');
  const gm2=gf2.append('feMerge');gm2.append('feMergeNode').attr('in','blur');gm2.append('feMergeNode').attr('in','SourceGraphic');
  const g=svg.append('g');
  svg.call(d3.zoom().scaleExtent([0.06,12]).on('zoom',e=>g.attr('transform',e.transform)));
  // dot grid
  const dg=g.append('g');
  for(let gx=-W;gx<W*2;gx+=28)for(let gy=-H;gy<H*2;gy+=28)
    dg.append('circle').attr('cx',gx).attr('cy',gy).attr('r',0.4).attr('fill','#0d0d1d');
  const link=g.append('g').selectAll('line').data(links).join('line')
    .attr('stroke',d=>d.type==='topic'?'#1e1e3e':'#14142a')
    .attr('stroke-width',d=>d.type==='topic'?0.8:0.4)
    .attr('stroke-dasharray',d=>d.type==='agent'?'2 7':null)
    .attr('opacity',d=>d.type==='topic'?0.7:0.3);
  const node=g.append('g').selectAll('g').data(nodes).join('g')
    .style('cursor',d=>d.type==='result'?'pointer':'default')
    .call(d3.drag()
      .on('start',(e,d)=>{if(!e.active)graphSimulation.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;})
      .on('drag',(e,d)=>{d.fx=e.x;d.fy=e.y;})
      .on('end',(e,d)=>{if(!e.active)graphSimulation.alphaTarget(0);d.fx=null;d.fy=null;})
    )
    .on('click',(e,d)=>{if(d.type==='result'&&d.data)openPopup(d.data,e.clientX,e.clientY);})
    .on('mouseenter',function(){d3.select(this).select('.gnm').attr('filter','url(#glow2)');})
    .on('mouseleave',function(){d3.select(this).select('.gnm').attr('filter','url(#glow)');});
  node.filter(d=>d.type==='topic').each(function(d){
    const s=d3.select(this);
    s.append('circle').attr('r',d.r+16).attr('fill','#ffffff').attr('opacity',0.02);
    s.append('circle').attr('class','gnm').attr('r',d.r).attr('fill','#0d0d1e').attr('stroke','#2a2a5e').attr('stroke-width',1).attr('filter','url(#glow)');
    s.append('circle').attr('r',3).attr('fill','#2a2a5e');
    s.append('text').attr('y',d.r+12).attr('text-anchor','middle').attr('fill','#3a3a7e').attr('font-family','Space Mono, Courier New').attr('font-size','8px').attr('letter-spacing','0.07em').text(d.label);
  });
  node.filter(d=>d.type==='result').each(function(d){
    const s=d3.select(this),c=d.color;
    s.append('circle').attr('r',d.r+10).attr('fill',c).attr('opacity',0.06);
    s.append('circle').attr('class','gnm').attr('r',d.r).attr('fill',c+'18').attr('stroke',c).attr('stroke-width',0.9).attr('stroke-opacity',0.65).attr('filter','url(#glow)');
    s.append('circle').attr('r',d.r*0.25).attr('fill',c).attr('opacity',0.85);
    if((d.data?.score||0)>=5||d.r>10)
      s.append('text').attr('y',d.r+11).attr('text-anchor','middle').attr('fill',c+'90').attr('font-family','Space Mono, Courier New').attr('font-size','7px').text(d.label.slice(0,16));
  });
  graphSimulation=d3.forceSimulation(nodes)
    .force('link',d3.forceLink(links).id(d=>d.id).distance(d=>d.type==='topic'?95:48).strength(d=>d.type==='topic'?0.5:0.2))
    .force('charge',d3.forceManyBody().strength(d=>d.type==='topic'?-290:-85))
    .force('center',d3.forceCenter(W/2,H/2))
    .force('collision',d3.forceCollide(d=>d.r+10));
  graphSimulation.on('tick',()=>{
    link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
    node.attr('transform',d=>`translate(${d.x},${d.y})`);
  });
}
function graphSearch(val){graphSearchTerm=val.toLowerCase().trim();buildGraph(filteredResults());}

// ═══════════════════════════════════════════════
// POPUP
// ═══════════════════════════════════════════════
function openPopup(res,cx,cy){
  const sc=res.score||0,cls=sc>=7?'hi':sc>=4?'mi':'lo';
  const ac=COL[res.agent]||'#7f77dd',def=agents.find(a=>a.key===res.agent);
  document.getElementById('p-badge').innerHTML=`<span class="pagent" style="background:${ac}18;color:${ac};border-color:${ac}40">${def?.icon||'🤖'} ${res.agent||''}</span>`;
  document.getElementById('p-topic').textContent=res.topic||'';
  document.getElementById('p-date').textContent=(res.created_at||'').slice(0,16).replace('T',' ');
  document.getElementById('p-score').innerHTML=sc>0?`<span class="pscore ${cls}">${sc}/10</span>`:'';
  document.getElementById('p-content').textContent=res.content||'';
  let tags=[];try{tags=typeof res.tags==='string'?JSON.parse(res.tags):(res.tags||[]);}catch(e){}
  document.getElementById('p-tags').innerHTML=tags.map(t=>`<span class="ptag" style="border-color:${ac}30;color:${ac}80">${t}</span>`).join('');
  const pop=document.getElementById('popup');
  pop.style.display='flex';requestAnimationFrame(()=>pop.classList.add('show'));
  const pw=510,ph=Math.min(window.innerHeight*0.76,560);
  let px=cx+18,py=cy-42;
  if(px+pw>window.innerWidth-270)px=cx-pw-18;
  if(py+ph>window.innerHeight-8)py=window.innerHeight-ph-8;
  if(py<8)py=8;px=Math.max(8,px);
  pop.style.left=px+'px';pop.style.top=py+'px';
}
function closePopup(){const pop=document.getElementById('popup');pop.classList.remove('show');setTimeout(()=>{pop.style.display='none';},230);}
document.getElementById('closebtn').addEventListener('click',closePopup);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closePopup();});

// ═══════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════
function showTab(id,el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));
  el.classList.add('on');document.getElementById('tab-'+id).classList.add('on');
}

function renderAgents(){
  document.getElementById('tab-agents').innerHTML=agents.map(a=>{
    const st=statuses[a.key],s=st?st.status:'unknown';
    const badge=s==='active'?'LIVE':s==='rate_limited'?'LIMITED':'OFFLINE';
    const tasks=st?.tasks_completed||0;
    const isLive=s==='active',isLim=s==='rate_limited';
    const badgeColor=isLive?'#1d9e75':isLim?'#ba7517':'#444';
    return `<div class="acard ${s}">
      <div class="actop" onclick="toggleDet('det-${a.key}')">
        <div class="acicon" style="background:${a.color}18;color:${a.color}">${a.icon||'🤖'}</div>
        <div class="acinfo">
          <div class="acname" style="color:${a.color}">${a.name}</div>
          <div class="acmodel">${a.fb[0]}</div>
        </div>
        <div class="acbadge ${s}" style="color:${badgeColor}">${badge}</div>
      </div>
      <div class="acdet" id="det-${a.key}">
        ${a.fb.map(f=>`<span>${f}</span>`).join('<br>')}
        <div class="det-row">
          <div class="det-col"><div class="det-lbl">TASKS</div><div class="det-val" style="color:${a.color}">${tasks}</div></div>
          <div class="det-col"><div class="det-lbl">STATUS</div><div class="det-val" style="color:${badgeColor}">${s}</div></div>
        </div>
      </div>
    </div>`;
  }).join('');
}

function toggleDet(id){document.getElementById(id)?.classList.toggle('show');}

function addFeed(agent,msg,color){
  const t=new Date().toTimeString().slice(0,5);
  feedLog.unshift({agent,msg,color,t});if(feedLog.length>40)feedLog.pop();
  document.getElementById('tab-feed').innerHTML=feedLog.map(f=>
    `<div class="fitem">
      <div class="fdot" style="background:${f.color}"></div>
      <div class="fbody">
        <div class="ftext"><strong style="color:${f.color}">${f.agent}</strong> ${f.msg}</div>
        <div class="ftime">${f.t}</div>
      </div>
    </div>`
  ).join('');
}

function renderInsights(){
  document.getElementById('tab-insights').innerHTML=allInsights.slice(0,10).map(i=>{
    const sc=i.novelty_score||0,cls=sc>=7?'hi':sc>=4?'mi':'lo';
    const preview=(i.content||'').replace(/[#*]/g,'').replace(/\n+/g,' ').slice(0,190);
    return `<div class="icard" onclick="openInsightPopup(${JSON.stringify(i).replace(/"/g,'&quot;')})">
      <span class="iscore ${cls}">novelty ${sc}/10</span>
      <div class="itext">${preview}…</div>
    </div>`;
  }).join('')||'<div style="padding:24px;font-size:10px;color:#333;text-align:center;line-height:2">No insights yet<br>Agents are still analyzing</div>';
}

function openInsightPopup(i){
  const fakeRes={agent:'synthesis',topic:'Synthesis Insight',content:i.content,score:i.novelty_score,tags:['insight','synthesis'],created_at:new Date().toISOString()};
  openPopup(fakeRes,window.innerWidth/2-255,window.innerHeight/2-200);
}

// ═══════════════════════════════════════════════
// FILTER
// ═══════════════════════════════════════════════
function setFilter(f,btn){
  activeFilter=f;
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('on'));btn.classList.add('on');
  const d=filteredResults();
  seedBubbles(d);
  if(currentView==='graph')buildGraph(d);
  setTimeout(()=>document.getElementById('bc').textContent=bubbles.length+' bubbles',2200);
}

// ═══════════════════════════════════════════════
// VIEW TOGGLE
// ═══════════════════════════════════════════════
function setView(v){
  currentView=v;
  document.getElementById('c').style.display=v==='canvas'?'block':'none';
  document.getElementById('graph-view').style.display=v==='graph'?'block':'none';
  document.getElementById('btn-canvas').classList.toggle('on',v==='canvas');
  document.getElementById('btn-graph').classList.toggle('on',v==='graph');
  if(v==='graph'){loopRunning=false;buildGraph(filteredResults());}
  else{loopRunning=true;requestAnimationFrame(loop);}
}

// ═══════════════════════════════════════════════
// EXPORT
// ═══════════════════════════════════════════════
function exportData(){
  const payload={exported_at:new Date().toISOString(),agents:agents.map(a=>({...a,status:statuses[a.key]})),results:allResults,insights:allInsights};
  const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download='research_export_'+Date.now()+'.json';a.click();
  URL.revokeObjectURL(url);
  addFeed('System','Research data exported to JSON ↓','#1d9e75');
}

// ═══════════════════════════════════════════════
// ADD AGENT MODAL
// ═══════════════════════════════════════════════
function openModal(){document.getElementById('modal').classList.add('show');}
function closeModal(){document.getElementById('modal').classList.remove('show');}
function selC(el){document.querySelectorAll('.cswatch').forEach(s=>s.classList.remove('sel'));el.classList.add('sel');selColor=el.dataset.c;}
document.getElementById('modal').addEventListener('click',e=>{if(e.target===document.getElementById('modal'))closeModal();});

function saveAgent(){
  const name=document.getElementById('m-name').value.trim();
  const role=document.getElementById('m-role').value.trim();
  const provider=document.getElementById('m-provider').value;
  if(!name||!role){alert('Please fill in agent name and research focus.');return;}
  const provMap={groq:'Groq (Llama 3.3 70B)',gemini:'Google Gemini 2.0 Flash',openrouter:'OpenRouter (Nemotron)',anthropic:'Anthropic Claude Sonnet'};
  const agentKey=name.toLowerCase().replace(/\s+/g,'_').replace(/[^a-z0-9_]/g,'');
  const icons=['🔬','🛰️','🌐','📡','🔭','⚙️','🧬','🗂️'];
  const newDef={key:agentKey,name,color:selColor,icon:icons[Math.floor(Math.random()*icons.length)],fb:[`Primary: ${provMap[provider]}`,`→ ${role.slice(0,40)}`],custom:true};
  agents.push(newDef);updateColors();
  statuses[agentKey]={status:'active',tasks_completed:0};
  const W=cv.width,H=cv.height;
  const positions=[{x:W*0.22,y:H*0.76},{x:W*0.71,y:H*0.80},{x:W*0.06,y:H*0.56},{x:W*0.44,y:H*0.44}];
  const ci=robots.filter(r=>r.custom).length;
  const pos=positions[ci%positions.length]||{x:W*0.5+Math.random()*80-40,y:H*0.5+Math.random()*80-40};
  const rb=new Robot(newDef,pos.x,pos.y);rb.custom=true;robots.push(rb);
  // add filter button
  const bar=document.getElementById('botbar'),btn=document.createElement('button');
  btn.className='fbtn';btn.textContent=name.slice(0,7);btn.onclick=function(){setFilter(agentKey,this);};
  bar.insertBefore(btn,document.getElementById('bc'));
  renderAgents();addFeed(name,'joined the research team 🎉',selColor);closeModal();
  document.getElementById('m-name').value='';document.getElementById('m-role').value='';document.getElementById('m-key').value='';
}

// ═══════════════════════════════════════════════
// SIMULATED LIVE UPDATES
// ═══════════════════════════════════════════════
function simulateLiveUpdate(){
  // randomly generate a new result
  const agentKey=AGENT_KEYS[Math.floor(Math.random()*AGENT_KEYS.length)];
  const newResult=generateResult(agentKey);
  allResults.unshift(newResult);
  if(allResults.length>200)allResults.pop();
  // update stats
  document.getElementById('s-total').textContent=allResults.length.toLocaleString();
  document.getElementById('s-topics').textContent=new Set(allResults.map(r=>r.topic)).size;
  // add bubble
  if(activeFilter==='all'||activeFilter===agentKey)addBubble(newResult);
  // feed
  const def=agents.find(a=>a.key===agentKey);
  addFeed(def?.name||agentKey,`"${newResult.topic.slice(0,34)}"`,COL[agentKey]||'#7f77dd');
  // graph update
  if(currentView==='graph')buildGraph(filteredResults());
  // tick
  const tk=document.getElementById('tick');tk.textContent='● LIVE';setTimeout(()=>tk.textContent='LIVE',500);
}

function simulateStatusFlip(){
  // randomly flip an agent's status
  const key=AGENT_KEYS[Math.floor(Math.random()*AGENT_KEYS.length)];
  const cur=statuses[key]?.status||'unknown';
  const next=cur==='active'?'rate_limited':cur==='rate_limited'?'active':'active';
  if(statuses[key])statuses[key].status=next;
  const def=agents.find(a=>a.key===key);
  if(next==='rate_limited')addFeed(def?.name||key,'rate limited → fallback triggered',COL[key]||'#555');
  if(next==='active')addFeed(def?.name||key,'back online ✓',COL[key]||'#555');
  document.getElementById('s-active').textContent=Object.values(statuses).filter(s=>s.status==='active').length;
  renderAgents();
}

// ═══════════════════════════════════════════════
// BOOT
// ═══════════════════════════════════════════════
const loadMessages=['INITIALIZING AGENTS…','LOADING KNOWLEDGE GRAPH…','STARTING PIPELINE…','HUB ONLINE ✓'];
let loadStep=0;
function bootLoader(){
  const fill=document.getElementById('load-fill');
  const sub=document.getElementById('load-sub');
  fill.style.width='25%';
  const iv=setInterval(()=>{
    loadStep++;
    fill.style.width=((loadStep+1)*25)+'%';
    sub.textContent=loadMessages[Math.min(loadStep,loadMessages.length-1)];
    if(loadStep>=3){clearInterval(iv);setTimeout(()=>{document.getElementById('loader').classList.add('hide');},500);}
  },500);
}

window.addEventListener('load',()=>{
  bootLoader();
  setTimeout(()=>{
    placeRobots();
    robots.forEach(r=>{const st=statuses[r.key];if(st)r.status=st.status||'unknown';});
    loop();
    renderAgents();
    renderInsights();
    const d=filteredResults();seedBubbles(d);
    document.getElementById('s-total').textContent=allResults.length.toLocaleString();
    document.getElementById('s-active').textContent=Object.values(statuses).filter(s=>s.status==='active').length;
    document.getElementById('s-topics').textContent=new Set(allResults.map(r=>r.topic)).size;
    addFeed('System','Hub online — click any bubble to read research','#7f77dd');
    addFeed('Pipeline','Scout → Analyst → Diver → Critic → Memory','#1d9e75');
    addFeed('System','Switch to ◈ GRAPH view for knowledge graph','#378add');
    // live updates
    setInterval(simulateLiveUpdate, 8000);
    setInterval(()=>{if(Math.random()<0.2)simulateStatusFlip();}, 15000);
    setInterval(()=>document.getElementById('s-time').textContent=new Date().toTimeString().slice(0,8),1000);
    setTimeout(()=>document.getElementById('bc').textContent=bubbles.length+' bubbles',4000);
    setTimeout(()=>document.getElementById('hint').style.opacity='0',8000);
  },2200);
});
</script>
</body>
</html>
