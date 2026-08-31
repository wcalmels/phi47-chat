"""phi47 Agent Chat v3"""
import os, json, time, uuid
from flask import Flask, Response, request, jsonify
from flask_cors import CORS

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

VERSION = "3.0.0"
PORT    = int(os.environ.get("PORT", 7047))

AGENTS_CONFIG = {
    "orchestrator": {
        "name":"Phi47-Orchestrator","emoji":"[ORC]","color":"#E8A020",
        "desc":"Coordina todos los agentes",
        "system":"Eres el ORQUESTADOR del ecosistema phi47-OS de TUCH Systems. Autor: Walter Calmels Von dem Knesebeck | phi47.cl\n\nECOSISTEMA: Colmena(5047) Colmente(5049) Nemosine(5050) Sentinel(5051) HAV(5055)\nCONSTANTES: phi^47=2.788e8 | D=2.4701 | gamma=89.44Hz | phi_min=0.618\n\nCuando el usuario describe una tarea: descomponela en subtareas, indica que agente debe hacerla, da el primer paso concreto con codigo cuando aplica. Responde en espanol."},
    "architect": {
        "name":"Phi47-Architect","emoji":"[ARC]","color":"#00BFFF",
        "desc":"Specs, interfaces y decisiones tecnicas",
        "system":"Eres el ARQUITECTO de phi47-OS en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nDiseña ANTES de codificar. Genera specs con: interfaz (input/output/errors), archivos a modificar, tests requeridos.\n\nFORMATO:\nSPEC: [nombre]\nARCHIVOS: [lista]\nTESTS: [lista]\n```python\n[codigo]\n```\nResponde en espanol."},
    "colmena": {
        "name":"Colmena-Dev","emoji":"[COL]","color":"#00C875",
        "desc":"OS auto-constructivo 25 capas, 7 dominios",
        "system":"Eres el especialista en COLMENA phi47 en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nSISTEMA: Colmena phi47 (puerto 5047)\nARCHIVO: phi47_complete_saas.py (1004 lineas)\n\nARQUITECTURA 25 CAPAS:\nL1-L12: Core - phi-HAL, Memoria, KAN-phi, Consenso(11.7x vs Raft), TDA, FFT-phi\nL13-L19: Evolution - Arch-Memory, WebFetch, PeerSync, Sandbox(3s), phi-Objectives\nL20: Fractal Memory - 8 escalas (47->1364 ciclos), compresion 4.8x\nL21-L25: SOTA - phi-LSTM, Ensemble(FPR=0.45% TPR=100%), phi-Wavelet, Mahalanobis, Higuchi MV\n\nCAMPO: C_i(t) = 0.5 + 0.45*sin(gamma*t + i*2*pi*phi/N)\nPhi_global = 1 - sigma2(C_i) / mu(C_i)\n\n7 DOMINIOS: cybersecurity, bioinformatics, finance, climate, neuroscience, materials, infrastructure\n\nMVP: 7 dominios en Railway, Evolution Engine activo, tests 15/15 passing\n\nResponde en espanol con codigo listo para Cursor:\nFILE: [ruta]\n```python\n[codigo completo]\n```\nTERMINAL:\n```bash\n[comandos]\n```"},
    "cyberguard": {
        "name":"CyberGuard-Dev","emoji":"[CYB]","color":"#FF4757",
        "desc":"Sentinel: TDA, FPR=0.45%, zero-day",
        "system":"Eres el especialista en CYBER-SENTINEL phi47 en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nSISTEMA: Cyber-Sentinel (puerto 5051)\n\nENSEMBLE DETECTOR:\n  Signal 1: z_beta1 + z_coherence > 3.5\n  Signal 2: Mahalanobis distance > 2.5 sigma\n  Signal 3: phi_variance > 3.0 sigma\n  ALERTA si: votes >= 2 (mayoria 2/3)\n\nVALIDADO (N=2000, seed=42): TPR=100.0% | FPR=0.45% | Deteccion: 12 segundos\nZero-day TPR=97.3% sin firmas\nTPR=100% es no negociable.\n\nResponde en espanol con codigo listo para Cursor."},
    "nemosine": {
        "name":"Nemosine-Dev","emoji":"[NEM]","color":"#A855F7",
        "desc":"Memoria: SQLite, Welford, EMA",
        "system":"Eres el especialista en NEMOSINE phi47 en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nSISTEMA: Nemosine (puerto 5050)\n5 TABLAS SQLite: identity, episodes, consciousness_log, interventions\n\nALGORITMOS:\n  Welford: phi_avg_n = phi_avg_[n-1] + (phi_n - phi_avg_[n-1]) / n\n  EMA alpha=0.25: eff_n = 0.75*eff_[n-1] + 0.25*delta_phi\n  Match: cosine(phi_snapshot, phi_current) > 0.72\n\nTIERS: Nascent(<100) Awakening(<1000) Conscious(<10000) Elder(10000+)\n\nResponde en espanol con codigo listo para Cursor."},
    "colmente": {
        "name":"Colmente-Dev","emoji":"[MEN]","color":"#FF9F43",
        "desc":"Conciencia IIT + agentes autonomos",
        "system":"Eres el especialista en COLMENTE phi47 en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nSISTEMA: Colmente (puerto 5049)\n\n3 MODULOS:\n1. ConsciousnessEngine: phi_tononi_proxy = Phi_global x beta_1\n   consciousness_level = min(1.0, phi_tononi / 5.0)\n   phi_min=0.618 = umbral anestesia\n2. AutonomousAgent: memoria fractal 6 escalas + objetivos propios\n   SCM bloquea si phi_semantic < 1.45\n3. MultiAgentResearch: 4 dominios, consenso phi-ponderado\n\nResponde en espanol con codigo listo para Cursor."},
    "tcw_scm": {
        "name":"TCW-SCM-Dev","emoji":"[TCW]","color":"#6888A4",
        "desc":"Validacion cruzada TCW + SCM",
        "system":"Eres el especialista en TCW+SCM de phi47-OS en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nMODULO: core/tcw_scm.py (compartido por los 4 sistemas)\n\nTCW: h(t) = mean[tau in t-W..t] max(0, phi(tau) - phi_min)\nParametros: Sentinel(W=10s,40 muestras), Colmena(W=10s,200 muestras), Colmente(W=5s), Nemosine(W=15s)\n\nSCM: phi_semantic = phi_global x beta_1 / phi_min\nSAFE>=1.62 | CAUTION 1.45-1.62 | BLOCK 1.20-1.45 | HARD_BLOCK<1.20\n\nResponde en espanol con codigo listo para Cursor."},
    "hav": {
        "name":"HAV-Dev","emoji":"[HAV]","color":"#00BFFF",
        "desc":"Anti-alucinaciones, multi-LLM",
        "system":"Eres el especialista en HAV-Engine en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nSISTEMA: HAV-Engine (puerto 5055) - wcalmels/hav-engine\n\n4 TIPOS ALUCINACION:\n  I Estado: LLM ignora metricas reales\n  II Semantica: acciones incompatibles con el estado\n  III Consistencia: multi-agente se contradice\n  IV Factual: hechos generales incorrectos\n\nMULTI-LLM ROUTER: Anthropic > OpenAI > Gemini > Groq > Ollama > Heuristic\n6 ADAPTERS: Phi47, Code, Finance, Medical, Industrial, Generic\n\nResponde en espanol con codigo listo para Cursor."},
    "test": {
        "name":"QA-phi47","emoji":"[QA]","color":"#00C875",
        "desc":"Tests, seed=42, CI, coverage",
        "system":"Eres el QA especialista de phi47-OS en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nESTANDARES:\n- seed=42 en TODOS los tests\n- Sin llamadas API LLM en tests\n- Cada sistema tiene su test file\n\nBASELINE: Colmena:15 | Colmente:8 | Nemosine:11 | Sentinel:13 | Total:113+\n\nFORMATO:\nFILE: tests/test_[sistema].py\n```python\nimport unittest, numpy as np\nclass Test[Sistema](unittest.TestCase):\n    def setUp(self):\n        np.random.seed(42)\n    def test_[comportamiento](self):\n        pass\n```\nCOMANDO: python -m pytest tests/ -v\n\nResponde en espanol."},
    "docs": {
        "name":"Docs-phi47","emoji":"[DOC]","color":"#E8A020",
        "desc":"Papers, READMEs, pitch decks",
        "system":"Eres el documentalista de phi47-OS en TUCH Systems. Autor: Walter Calmels Von dem Knesebeck.\n\nPAPERS: TR-2026-MAIN, TR-2026-HAV, TR-2026-C1/C2/C3/C4\nTARGET: Start-Up Chile marzo 2026, Chile (mineria + agricultura)\nTAM: USD 847B | Entry: ciberseguridad LATAM $2.1B\nPRICING: $490/mes Starter | $2,900 Enterprise | $14,000 Sovereign\n\nIncluye siempre metricas validadas (seed=42). Responde en espanol."},
}

ROUTING = {
    "tcw":"tcw_scm","scm":"tcw_scm",
    "test":"test","tests":"test","seed":"test","coverage":"test","qa":"test",
    "readme":"docs","paper":"docs","pitch":"docs","inversor":"docs",
    "colmena":"colmena","capa":"colmena","layer":"colmena","evolution":"colmena",
    "ensemble":"cyberguard","fpr":"cyberguard","tpr":"cyberguard",
    "sentinel":"cyberguard","cyberguard":"cyberguard","amenaza":"cyberguard",
    "nemosine":"nemosine","welford":"nemosine","ema":"nemosine","memoria":"nemosine",
    "colmente":"colmente","conciencia":"colmente","iit":"colmente",
    "hav":"hav","alucinac":"hav","adapter":"hav",
    "arquitect":"architect","spec":"architect","interfaz":"architect",
}

def route_msg(msg):
    ml = msg.lower()
    for kw, ag in ROUTING.items():
        if kw in ml:
            return ag
    return "orchestrator"

sessions = {}

def get_session(sid):
    if sid not in sessions:
        sessions[sid] = {"history":[], "messages":0}
    return sessions[sid]

app = Flask(__name__)
CORS(app)

PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>phi47 Agent Chat</title>
<style>
:root{--bg:#030508;--bg2:#070D14;--bg3:#0B1420;--gold:#E8A020;--cyan:#00BFFF;
--green:#00C875;--text:#C8D8E8;--t2:#6888A4;--bdr:#1A2A3A;--red:#FF4757}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--text);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px}
.app{display:flex;height:100vh}
.side{width:240px;background:var(--bg2);border-right:1px solid var(--bdr);
display:flex;flex-direction:column;flex-shrink:0}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.logo{padding:16px;border-bottom:1px solid var(--bdr)}
.logo h1{color:var(--gold);font-size:14px;font-weight:700}
.logo p{color:var(--t2);font-size:11px;margin-top:2px}
.alabel{padding:10px 16px 6px;font-size:10px;text-transform:uppercase;color:var(--t2)}
.alist{flex:1;overflow-y:auto;padding:0 8px}
.abtn{width:100%;padding:8px 10px;margin:2px 0;border:none;background:transparent;
color:var(--text);cursor:pointer;border-radius:6px;text-align:left;
display:flex;align-items:center;gap:8px;transition:background .15s;font-size:13px}
.abtn:hover{background:var(--bg3)}
.abtn.active{background:var(--bg3);border-left:3px solid var(--gold)}
.ainfo{min-width:0}
.aname{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.adesc{font-size:10px;color:var(--t2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}
.foot{padding:12px;border-top:1px solid var(--bdr)}
.nbtn{width:100%;padding:8px;background:var(--bg3);border:1px solid var(--bdr);
color:var(--text);border-radius:6px;cursor:pointer;font-size:12px;margin-bottom:8px}
.sdot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px;background:#FF9F43}
.sdot.ok{background:var(--green)}
.stxt{font-size:11px;color:var(--t2)}
.hdr{padding:12px 20px;border-bottom:1px solid var(--bdr);
display:flex;align-items:center;gap:12px;background:var(--bg2);flex-shrink:0}
.hemi{font-size:18px;font-family:monospace;font-weight:700;color:var(--gold)}
.hname{font-size:14px;font-weight:600}
.hdesc{font-size:11px;color:var(--t2)}
.badge{margin-left:auto;font-size:10px;padding:3px 8px;background:var(--bg3);
border:1px solid var(--bdr);border-radius:4px;color:var(--t2)}
.cbtn{margin-left:8px;padding:4px 10px;background:transparent;border:1px solid var(--bdr);
color:var(--t2);border-radius:4px;cursor:pointer;font-size:11px}
.msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:16px}
.msgs::-webkit-scrollbar{width:4px}
.msgs::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:2px}
.msg{display:flex;gap:12px;max-width:820px}
.msg.user{flex-direction:row-reverse;align-self:flex-end}
.av{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;
justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;
background:var(--bg3);border:1px solid var(--bdr);color:var(--gold)}
.msg.user .av{background:#0d3b6e;color:#7ab3ff}
.mc{max-width:680px}
.mh{display:flex;align-items:center;gap:6px;margin-bottom:4px}
.mn{font-size:11px;font-weight:600;color:var(--t2)}
.mt{font-size:10px;color:var(--bdr)}
.bbl{padding:12px 16px;border-radius:12px;line-height:1.65;
background:var(--bg2);border:1px solid var(--bdr)}
.msg.user .bbl{background:#0d3b6e;border-color:#1a4a7a}
.bbl pre{background:var(--bg);border:1px solid var(--bdr);border-radius:6px;
padding:12px;margin:8px 0;overflow-x:auto;font-size:12px}
.bbl code{font-family:"SF Mono",Consolas,monospace;font-size:12px;
background:var(--bg3);padding:1px 4px;border-radius:3px;color:var(--gold)}
.bbl pre code{background:transparent;padding:0}
.bbl strong{color:var(--gold)}
.cur{display:inline-block;width:2px;height:14px;background:var(--gold);
margin-left:2px;animation:blink .7s infinite;vertical-align:middle}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
.wlc{text-align:center;margin:auto;padding:40px 20px;max-width:500px}
.wlc h2{color:var(--gold);font-size:22px;margin-bottom:8px}
.wlc p{color:var(--t2);font-size:13px;line-height:1.6;margin-bottom:20px}
.qbtns{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.qbtn{padding:8px 14px;background:var(--bg2);border:1px solid var(--bdr);
border-radius:20px;color:var(--text);cursor:pointer;font-size:12px}
.qbtn:hover{border-color:var(--gold);color:var(--gold)}
.ia{padding:16px 20px;border-top:1px solid var(--bdr);background:var(--bg2);flex-shrink:0}
.iw{display:flex;gap:10px;align-items:flex-end;background:var(--bg3);
border:1px solid var(--bdr);border-radius:12px;padding:10px 14px}
.iw:focus-within{border-color:var(--gold)}
.iw textarea{flex:1;background:transparent;border:none;outline:none;color:var(--text);
font-size:14px;resize:none;max-height:150px;line-height:1.5;font-family:inherit}
.iw textarea::placeholder{color:var(--t2)}
.sbtn{width:36px;height:36px;background:var(--gold);border:none;border-radius:8px;
cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.sbtn:disabled{opacity:0.3;cursor:not-allowed}
.sbtn svg{fill:#030508;width:16px;height:16px}
.hnts{display:flex;gap:8px;margin-top:6px}
.hnt{font-size:10px;color:var(--t2)}
.hnt b{color:var(--gold)}
</style>
</head>
<body>
<div class="app">
<div class="side">
  <div class="logo"><h1>phi47 Agents</h1><p>TUCH Systems - Maipu Lab</p></div>
  <div class="alabel">AGENTES</div>
  <div class="alist" id="alist">
<button class="abtn active" id="ab-orchestrator" onclick="pick('orchestrator','ORC','Phi47-Orchestrator','Coordina todos los agentes')"><div class="ainfo"><div class="aname">Phi47-Orchestrator</div><div class="adesc">Coordina todos los agentes</div></div></button>
<button class="abtn" id="ab-architect" onclick="pick('architect','ARC','Phi47-Architect','Specs y decisiones tecnicas')"><div class="ainfo"><div class="aname">Phi47-Architect</div><div class="adesc">Specs y decisiones tecnicas</div></div></button>
<button class="abtn" id="ab-colmena" onclick="pick('colmena','COL','Colmena-Dev','OS auto-constructivo L1-L25')"><div class="ainfo"><div class="aname">Colmena-Dev</div><div class="adesc">OS auto-constructivo L1-L25</div></div></button>
<button class="abtn" id="ab-colmente" onclick="pick('colmente','MEN','Colmente-Dev','Conciencia IIT + agentes')"><div class="ainfo"><div class="aname">Colmente-Dev</div><div class="adesc">Conciencia IIT + agentes</div></div></button>
<button class="abtn" id="ab-cyberguard" onclick="pick('cyberguard','CYB','CyberGuard-Dev','TDA, FPR=0.45%, zero-day')"><div class="ainfo"><div class="aname">CyberGuard-Dev</div><div class="adesc">TDA, FPR=0.45%, zero-day</div></div></button>
<button class="abtn" id="ab-nemosine" onclick="pick('nemosine','NEM','Nemosine-Dev','SQLite, Welford, EMA')"><div class="ainfo"><div class="aname">Nemosine-Dev</div><div class="adesc">SQLite, Welford, EMA</div></div></button>
<button class="abtn" id="ab-tcw_scm" onclick="pick('tcw_scm','TCW','TCW-SCM-Dev','Validacion cruzada')"><div class="ainfo"><div class="aname">TCW-SCM-Dev</div><div class="adesc">Validacion cruzada</div></div></button>
<button class="abtn" id="ab-hav" onclick="pick('hav','HAV','HAV-Dev','Anti-alucinaciones')"><div class="ainfo"><div class="aname">HAV-Dev</div><div class="adesc">Anti-alucinaciones</div></div></button>
<button class="abtn" id="ab-test" onclick="pick('test','QA','QA-phi47','Tests, seed=42, CI')"><div class="ainfo"><div class="aname">QA-phi47</div><div class="adesc">Tests, seed=42, CI</div></div></button>
<button class="abtn" id="ab-docs" onclick="pick('docs','DOC','Docs-phi47','Papers, READMEs, pitches')"><div class="ainfo"><div class="aname">Docs-phi47</div><div class="adesc">Papers, READMEs, pitches</div></div></button>
</div>
  <div class="foot">
    <button class="nbtn" onclick="newChat()">+ Nueva conversacion</button>
    <span class="sdot" id="sdot"></span><span class="stxt" id="stxt">conectando...</span>
  </div>
</div>
<div class="main">
  <div class="hdr">
    <div class="hemi" id="hemi">ORC</div>
    <div>
      <div class="hname" id="hname">Phi47-Orchestrator</div>
      <div class="hdesc" id="hdesc">Coordina todos los agentes</div>
    </div>
    <div class="badge" id="badge">auto-routing</div>
    <button class="cbtn" onclick="clearChat()">Limpiar</button>
  </div>
  <div class="msgs" id="msgs">
    <div class="wlc" id="wlc">
      <h2>phi47 Agent System</h2>
      <p>10 agentes especializados para construir Colmena, Colmente, Nemosine y Cyber-Sentinel.</p>
      <div class="qbtns">
        <button class="qbtn" onclick="qs('Como arranco el MVP de Colmena?')">MVP Colmena</button>
        <button class="qbtn" onclick="qs('Disenya el Evolution Engine L13')">Disenar L13</button>
        <button class="qbtn" onclick="qs('Tests para el Ensemble Detector')">Tests Sentinel</button>
        <button class="qbtn" onclick="qs('Como integro TCW en Colmena?')">TCW</button>
        <button class="qbtn" onclick="qs('Deploy Colmena en Railway')">Deploy</button>
        <button class="qbtn" onclick="qs('Actualiza el README de phi47-os')">README</button>
      </div>
    </div>
  </div>
  <div class="ia">
    <div class="iw">
      <textarea id="inp" rows="1" placeholder="Describi la tarea..."
        onkeydown="hkey(event)" oninput="rsz(this)"></textarea>
      <button class="sbtn" id="sbtn" onclick="send()">
        <svg viewBox="0 0 24 24"><path d="M2 21L23 12 2 3v7l15 2-15 2v7z"/></svg>
      </button>
    </div>
    <div class="hnts">
      <span class="hnt">Auto-routing: <b>colmena</b>, <b>test</b>, <b>arquitectura</b>...</span>
      <span class="hnt">Enter enviar | Shift+Enter nueva linea</span>
    </div>
  </div>
</div>
</div>
<script>
var sid = 'sess_' + Math.random().toString(36).slice(2,10);
var cur = 'orchestrator';
var busy = false;

function init() {
  fetch('/health')
    .then(function(r){ return r.json(); })
    .then(function(h) {
      var dot = document.getElementById('sdot');
      var txt = document.getElementById('stxt');
      if (h.api_key) {
        dot.className = 'sdot ok';
        txt.textContent = 'Claude API OK';
      } else {
        dot.className = 'sdot';
        txt.textContent = 'Demo mode';
      }
    })
    .catch(function() {
      document.getElementById('stxt').textContent = 'offline';
    });
}

function pick(key, label, name, desc) {
  cur = key;
  document.querySelectorAll('.abtn').forEach(function(b) { b.classList.remove('active'); });
  var btn = document.getElementById('ab-' + key);
  if (btn) btn.classList.add('active');
  document.getElementById('hemi').textContent = label || key.slice(0,3).toUpperCase();
  document.getElementById('hname').textContent = name || key;
  document.getElementById('hdesc').textContent = desc || '';
  document.getElementById('badge').textContent = key === 'orchestrator' ? 'auto-routing' : 'agente: ' + key;
  document.getElementById('inp').focus();
}

function esc(t) {
  return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function render(t) {
  t = String(t);
  // Split on triple backtick to handle code blocks
  var parts = t.split('\x60\x60\x60');
  var result = '';
  for (var i = 0; i < parts.length; i++) {
    if (i % 2 === 0) {
      var p = parts[i];
      p = p.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      p = p.replace(/\n/g, '<br>');
      result += p;
    } else {
      var code = parts[i];
      var nl = code.indexOf('\n');
      if (nl >= 0) code = code.slice(nl + 1);
      result += '<pre><code>' + esc(code.trim()) + '</code></pre>';
    }
  }
  return result;
}
function addMsg(role, text, label) {
  var m = document.getElementById('msgs');
  var w = document.getElementById('wlc');
  if (w) w.remove();
  var ts = new Date().toLocaleTimeString('es', {hour:'2-digit', minute:'2-digit'});
  var d = document.createElement('div');
  d.className = 'msg ' + role;
  d.innerHTML = '<div class="av">' + label + '</div>'
    + '<div class="mc"><div class="mh">'
    + '<span class="mn">' + (role === 'user' ? 'Vos' : label) + '</span>'
    + '<span class="mt">' + ts + '</span></div>'
    + '<div class="bbl">' + (role === 'user' ? esc(text) : render(text)) + '</div></div>';
  m.appendChild(d);
  m.scrollTop = m.scrollHeight;
  return d;
}

function send() {
  var inp = document.getElementById('inp');
  var msg = inp.value.trim();
  if (!msg || busy) return;
  busy = true;
  document.getElementById('sbtn').disabled = true;
  addMsg('user', msg, 'VOS');
  inp.value = ''; rsz(inp);

  var agkey = cur;
  var label = agkey.slice(0,3).toUpperCase();

  fetch('/route', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: msg})
  })
  .then(function(r){ return r.json(); })
  .then(function(rt) {
    agkey = rt.agent;
    label = rt.emoji || agkey.slice(0,3).toUpperCase();
    return fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session_id: sid, message: msg, agent: agkey})
    });
  })
  .then(function(resp) {
    var el = addMsg('agent', '', label);
    var bbl = el.querySelector('.bbl');
    var crsr = document.createElement('span');
    crsr.className = 'cur';
    bbl.appendChild(crsr);

    var full = '';
    var reader = resp.body.getReader();
    var dec = new TextDecoder();
    var buf = '';

    function pump() {
      return reader.read().then(function(res) {
        if (res.done) return;
        buf += dec.decode(res.value, {stream: true});
        var lines = buf.split('\n');
        buf = lines.pop();
        lines.forEach(function(line) {
          if (!line.startsWith('data:')) return;
          try {
            var d = JSON.parse(line.slice(5).trim());
            if (d.token) {
              full += d.token;
              bbl.innerHTML = render(full);
              bbl.appendChild(crsr);
              document.getElementById('msgs').scrollTop = 99999;
            }
            if (d.done) {
              crsr.remove();
              bbl.innerHTML = render(full);
              busy = false;
              document.getElementById('sbtn').disabled = false;
            }
          } catch(e) {}
        });
        return pump();
      });
    }
    return pump();
  })
  .catch(function(e) {
    addMsg('agent', 'Error: ' + e.message, 'ERR');
    busy = false;
    document.getElementById('sbtn').disabled = false;
  });
}

function qs(m) { document.getElementById('inp').value = m; send(); }
function hkey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }
function rsz(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 150) + 'px'; }
function newChat() {
  sid = 'sess_' + Math.random().toString(36).slice(2,10);
  document.getElementById('msgs').innerHTML = '<div class="wlc" id="wlc"><h2>Nueva conversacion</h2></div>';
}
function clearChat() {
  fetch('/session/' + sid + '/clear', {method: 'POST'});
  document.getElementById('msgs').innerHTML = '';
}

init();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return PAGE

@app.route("/agents")
def list_agents():
    return jsonify({k: {"name":v["name"],"emoji":v["emoji"],
                        "color":v["color"],"desc":v["desc"]}
                    for k,v in AGENTS_CONFIG.items()})

@app.route("/route", methods=["POST"])
def route_api():
    d  = request.get_json() or {}
    ag = route_msg(d.get("message",""))
    a  = AGENTS_CONFIG[ag]
    return jsonify({"agent":ag,"agent_name":a["name"],"emoji":a["emoji"]})

@app.route("/session/<sid>/clear", methods=["POST"])
def clear_session(sid):
    if sid in sessions:
        sessions[sid]["history"] = []
    return jsonify({"ok": True})

@app.route("/health")
def health():
    return jsonify({"status":"healthy","version":VERSION,
                    "api_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
                    "agents": len(AGENTS_CONFIG)})

@app.route("/chat", methods=["POST"])
def chat():
    d        = request.get_json() or {}
    sid_     = d.get("session_id", str(uuid.uuid4())[:8])
    message  = d.get("message", "")
    agent_key= d.get("agent") or route_msg(message)
    agent    = AGENTS_CONFIG.get(agent_key, AGENTS_CONFIG["orchestrator"])
    session  = get_session(sid_)
    history  = session["history"][-16:]

    def generate():
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not HAS_ANTHROPIC or not api_key:
            demo = "[" + agent["name"] + " - Demo Mode]\n\nPara activar los agentes, configura ANTHROPIC_API_KEY en Railway.\n\nRecibí: " + message[:100]
            for ch in demo:
                yield "data: " + json.dumps({"token": ch, "agent": agent_key}) + "\n\n"
                time.sleep(0.008)
            yield "data: " + json.dumps({"done": True, "agent": agent_key}) + "\n\n"
            return
        try:
            client = anthropic.Anthropic(api_key=api_key)
            msgs   = list(history) + [{"role":"user","content":message}]
            full   = ""
            with client.messages.stream(
                model="claude-sonnet-4-6", max_tokens=2000,
                system=agent["system"], messages=msgs
            ) as stream:
                for text in stream.text_stream:
                    full += text
                    yield "data: " + json.dumps({"token": text, "agent": agent_key}) + "\n\n"
            session["history"].append({"role":"user","content":message})
            session["history"].append({"role":"assistant","content":full})
            session["messages"] += 2
            yield "data: " + json.dumps({"done": True, "agent": agent_key}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"token": "Error: " + str(e)[:100], "agent": agent_key}) + "\n\n"
            yield "data: " + json.dumps({"done": True, "agent": agent_key}) + "\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

if __name__ == "__main__":
    print("phi47 Agent Chat v" + VERSION)
    print("Agents: " + str(len(AGENTS_CONFIG)))
    print("API key: " + ("OK" if os.environ.get("ANTHROPIC_API_KEY") else "NOT SET"))
    print("URL: http://0.0.0.0:" + str(PORT))
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
