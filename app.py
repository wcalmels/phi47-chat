"""phi47 Agent Chat - Final Clean Version"""
import os, json, time, uuid
from flask import Flask, Response, request, jsonify
from flask_cors import CORS

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

PORT = int(os.environ.get("PORT", 7047))

AGENTS = {
    "orchestrator": {"name":"Phi47-Orchestrator","desc":"Coordina todos los agentes","system":"Eres el ORQUESTADOR del ecosistema phi47-OS. Autor: Walter Calmels Von dem Knesebeck | phi47.cl\n\nECOSISTEMA: Colmena(5047) Colmente(5049) Nemosine(5050) Sentinel(5051) HAV(5055)\nCONSTANTES: phi^47=2.788e8 | phi_min=0.618\n\nDescompone tareas, indica que agente debe hacerla, da codigo cuando aplica. Responde en espanol."},
    "architect":    {"name":"Phi47-Architect","desc":"Specs y decisiones tecnicas","system":"Eres el ARQUITECTO de phi47-OS. Autor: Walter Calmels Von dem Knesebeck.\nDisenya ANTES de codificar. Da specs con archivos, interfaces y tests. Responde en espanol."},
    "colmena":      {"name":"Colmena-Dev","desc":"OS auto-constructivo L1-L25","system":"Eres especialista en COLMENA phi47 (puerto 5047). Autor: Walter Calmels Von dem Knesebeck.\n25 CAPAS: L1-L12 Core, L13-L19 Evolution, L20 Fractal Memory, L21-L25 SOTA.\nCampo: C_i(t)=0.5+0.45*sin(gamma*t+i*2*pi*phi/N). 7 dominios. MVP en Railway.\nResponde en espanol con codigo para Cursor."},
    "cyberguard":   {"name":"CyberGuard-Dev","desc":"TDA, FPR=0.45%, zero-day","system":"Eres especialista en CYBER-SENTINEL phi47 (puerto 5051). Autor: Walter Calmels Von dem Knesebeck.\nENSEMBLE: z_beta1+z_coh>3.5, Mahalanobis>2.5sigma, phi_var>3sigma. ALERTA si votes>=2.\nTPR=100% FPR=0.45% en 12s. Responde en espanol."},
    "nemosine":     {"name":"Nemosine-Dev","desc":"SQLite, Welford, EMA","system":"Eres especialista en NEMOSINE phi47 (puerto 5050). Autor: Walter Calmels Von dem Knesebeck.\n5 tablas SQLite. Welford online. EMA alpha=0.25. Cosine>0.72 match.\nTiers: Nascent<100, Awakening<1000, Conscious<10000, Elder. Responde en espanol."},
    "colmente":     {"name":"Colmente-Dev","desc":"IIT + agentes autonomos","system":"Eres especialista en COLMENTE phi47 (puerto 5049). Autor: Walter Calmels Von dem Knesebeck.\nphi_tononi=Phi_global*beta1. SCM bloquea si phi_semantic<1.45. Responde en espanol."},
    "tcw_scm":      {"name":"TCW-SCM-Dev","desc":"Validacion cruzada","system":"Eres especialista en TCW+SCM. Autor: Walter Calmels Von dem Knesebeck.\nTCW: h(t)=mean[phi(tau)-phi_min]. SCM: phi_semantic=phi_global*beta1/phi_min.\nSAFE>=1.62, CAUTION>=1.45, BLOCK>=1.20. Responde en espanol."},
    "hav":          {"name":"HAV-Dev","desc":"Anti-alucinaciones","system":"Eres especialista en HAV-Engine (puerto 5055). Autor: Walter Calmels Von dem Knesebeck.\n4 tipos: I Estado, II Semantica, III Consistencia, IV Factual.\nRouter: Anthropic>OpenAI>Gemini>Groq>Ollama. Responde en espanol."},
    "test":         {"name":"QA-phi47","desc":"Tests, seed=42, CI","system":"Eres QA especialista de phi47-OS. Autor: Walter Calmels Von dem Knesebeck.\nseed=42 en TODOS los tests. Sin API LLM en tests. Baseline: 113+ tests. Responde en espanol."},
    "docs":         {"name":"Docs-phi47","desc":"Papers, READMEs, pitches","system":"Eres documentalista de phi47-OS. Autor: Walter Calmels Von dem Knesebeck.\nTR-2026-MAIN, TR-2026-HAV. Start-Up Chile marzo 2026. TAM USD 847B. Responde en espanol."},
}

ROUTING = {
    "tcw":"tcw_scm","scm":"tcw_scm","test":"test","tests":"test","seed":"test","qa":"test",
    "readme":"docs","paper":"docs","pitch":"docs","colmena":"colmena","capa":"colmena",
    "layer":"colmena","evolution":"colmena","ensemble":"cyberguard","fpr":"cyberguard",
    "tpr":"cyberguard","sentinel":"cyberguard","nemosine":"nemosine","welford":"nemosine",
    "ema":"nemosine","colmente":"colmente","conciencia":"colmente","iit":"colmente",
    "hav":"hav","alucinac":"hav","arquitect":"architect","spec":"architect",
}

def route_msg(msg):
    ml = msg.lower()
    for kw, ag in ROUTING.items():
        if kw in ml: return ag
    return "orchestrator"

sessions = {}
def get_session(sid):
    if sid not in sessions:
        sessions[sid] = {"history":[]}
    return sessions[sid]

app = Flask(__name__)
CORS(app)

AGENTS_JS = json.dumps({k:{"name":v["name"],"desc":v["desc"]} for k,v in AGENTS.items()})

PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>phi47 Agents</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{display:flex;height:100vh;background:#030508;color:#C8D8E8;font-family:system-ui,sans-serif;font-size:14px}
#side{width:220px;background:#070D14;border-right:1px solid #1A2A3A;display:flex;flex-direction:column;flex-shrink:0}
#main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.logo{padding:14px;border-bottom:1px solid #1A2A3A;color:#E8A020;font-weight:700;font-size:13px}
.logo small{display:block;color:#6888A4;font-size:10px;font-weight:400;margin-top:2px}
#alist{flex:1;overflow-y:auto;padding:6px}
.ab{width:100%;padding:7px 9px;margin:1px 0;border:none;background:transparent;color:#C8D8E8;cursor:pointer;border-radius:5px;text-align:left;font-size:12px;font-weight:600;display:block}
.ab:hover,.ab.on{background:#0B1420;border-left:2px solid #E8A020;color:#E8A020}
.ab small{display:block;font-size:10px;color:#6888A4;font-weight:400;margin-top:1px}
#foot{padding:10px;border-top:1px solid #1A2A3A;font-size:11px;color:#6888A4}
#hdr{padding:10px 18px;background:#070D14;border-bottom:1px solid #1A2A3A;display:flex;align-items:center;gap:10px;flex-shrink:0}
#badge{margin-left:auto;font-size:10px;padding:2px 7px;background:#0B1420;border:1px solid #1A2A3A;border-radius:3px;color:#6888A4}
#msgs{flex:1;overflow-y:auto;padding:18px;display:flex;flex-direction:column;gap:14px}
.mu{align-self:flex-end;max-width:70%}
.ma{align-self:flex-start;max-width:80%}
.mlabel{font-size:10px;color:#6888A4;margin-bottom:3px}
.mbbl{padding:10px 14px;border-radius:10px;line-height:1.6}
.mu .mbbl{background:#0d3b6e;border:1px solid #1a4a7a}
.ma .mbbl{background:#070D14;border:1px solid #1A2A3A}
.mbbl pre{background:#030508;border:1px solid #1A2A3A;border-radius:5px;padding:10px;margin:6px 0;overflow-x:auto;font-size:12px;white-space:pre-wrap}
.cur{display:inline-block;width:2px;height:13px;background:#E8A020;margin-left:2px;animation:bl .7s infinite;vertical-align:middle}
@keyframes bl{0%,100%{opacity:1}50%{opacity:0}}
#ia{padding:14px 18px;background:#070D14;border-top:1px solid #1A2A3A;flex-shrink:0}
#irow{display:flex;gap:8px;align-items:flex-end;background:#0B1420;border:1px solid #1A2A3A;border-radius:10px;padding:8px 12px}
#irow:focus-within{border-color:#E8A020}
#inp{flex:1;background:transparent;border:none;outline:none;color:#C8D8E8;font-size:14px;resize:none;max-height:120px;font-family:inherit;line-height:1.5}
#inp::placeholder{color:#6888A4}
#sbtn{width:34px;height:34px;background:#E8A020;border:none;border-radius:7px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center}
#sbtn:disabled{opacity:.3;cursor:not-allowed}
#sbtn svg{fill:#030508;width:15px;height:15px}
.hint{font-size:10px;color:#6888A4;margin-top:5px}
.hint b{color:#E8A020}
#wlc{text-align:center;margin:auto;padding:40px 20px;max-width:480px}
#wlc h2{color:#E8A020;font-size:20px;margin-bottom:8px}
#wlc p{color:#6888A4;font-size:13px;line-height:1.6;margin-bottom:18px}
.qb{display:inline-block;margin:3px;padding:7px 13px;background:#070D14;border:1px solid #1A2A3A;border-radius:16px;color:#C8D8E8;cursor:pointer;font-size:12px}
.qb:hover{border-color:#E8A020;color:#E8A020}
</style>
</head>
<body>
<div id="side">
  <div class="logo">phi47 Agents<small>TUCH Systems - Maipu Lab</small></div>
  <div id="alist"></div>
  <div id="foot">conectando...</div>
</div>
<div id="main">
  <div id="hdr">
    <div>
      <strong id="hname">Phi47-Orchestrator</strong><br>
      <small id="hdesc">Coordina todos los agentes</small>
    </div>
    <div id="badge">auto-routing</div>
  </div>
  <div id="msgs">
    <div id="wlc">
      <h2>phi47 Agent System</h2>
      <p>10 agentes especializados para construir el ecosistema phi47-OS.</p>
      <div id="qbtns"></div>
    </div>
  </div>
  <div id="ia">
    <div id="irow">
      <textarea id="inp" rows="1" placeholder="Describi la tarea..."></textarea>
      <button id="sbtn"><svg viewBox="0 0 24 24"><path d="M2 21L23 12 2 3v7l15 2-15 2v7z"/></svg></button>
    </div>
    <div class="hint">Auto-routing: <b>colmena</b>, <b>test</b>, <b>tcw</b>... | Enter enviar | Shift+Enter nueva linea</div>
  </div>
</div>

<script>
(function() {

var AG = """ + AGENTS_JS + """;

var QUICK = [
  ['Como arranco el MVP de Colmena?', 'MVP Colmena'],
  ['Disenya el Evolution Engine L13', 'Disenar L13'],
  ['Tests para Ensemble Detector', 'Tests Sentinel'],
  ['Como integro TCW en Colmena?', 'TCW'],
  ['Deploy Colmena en Railway', 'Deploy'],
  ['README actualizado phi47-os', 'README']
];

var sid = 'sess_' + Math.random().toString(36).slice(2,10);
var cur = 'orchestrator';
var busy = false;

function G(id) { return document.getElementById(id); }

// Build sidebar
var list = G('alist');
Object.keys(AG).forEach(function(key) {
  var a = AG[key];
  var btn = document.createElement('button');
  btn.className = 'ab' + (key === 'orchestrator' ? ' on' : '');
  btn.id = 'ab-' + key;
  btn.innerHTML = a.name + '<small>' + a.desc + '</small>';
  btn.addEventListener('click', function() {
    cur = key;
    document.querySelectorAll('.ab').forEach(function(b) { b.classList.remove('on'); });
    btn.classList.add('on');
    G('hname').textContent = a.name;
    G('hdesc').textContent = a.desc;
    G('badge').textContent = key === 'orchestrator' ? 'auto-routing' : key;
    G('inp').focus();
  });
  list.appendChild(btn);
});

// Build quick buttons
var qc = G('qbtns');
QUICK.forEach(function(q) {
  var b = document.createElement('span');
  b.className = 'qb';
  b.textContent = q[1];
  b.addEventListener('click', function() {
    G('inp').value = q[0];
    doSend();
  });
  qc.appendChild(b);
});

// Health check
fetch('/health')
  .then(function(r) { return r.json(); })
  .then(function(h) {
    var f = G('foot');
    if (h.api_key) {
      f.textContent = 'Claude API OK';
      f.style.color = '#00C875';
    } else {
      f.textContent = 'Demo mode';
      f.style.color = '#FF9F43';
    }
  })
  .catch(function() { G('foot').textContent = 'offline'; });

function addMsg(role, text) {
  var w = G('wlc');
  if (w) w.remove();
  var msgs = G('msgs');
  var d = document.createElement('div');
  d.className = role === 'user' ? 'mu' : 'ma';
  var label = role === 'user' ? 'Vos' : AG[cur].name;
  d.innerHTML = '<div class="mlabel">' + label + '</div><div class="mbbl"></div>';
  msgs.appendChild(d);
  var bbl = d.querySelector('.mbbl');
  if (text) bbl.textContent = text;
  msgs.scrollTop = msgs.scrollHeight;
  return bbl;
}

function renderMD(t) {
  var html = '';
  var parts = t.split('```');
  for (var i = 0; i < parts.length; i++) {
    if (i % 2 === 0) {
      var p = parts[i]
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/[*][*]([^*]+)[*][*]/g,'<strong style="color:#E8A020">$1</strong>');
      html += p.replace(/\n/g,'<br>');
    } else {
      var code = parts[i];
      var nl = code.indexOf('\n');
      if (nl >= 0) code = code.slice(nl+1);
      html += '<pre>' + code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</pre>';
    }
  }
  return html;
}

function doSend() {
  if (busy) return;
  var msg = G('inp').value.trim();
  if (!msg) return;

  busy = true;
  G('sbtn').disabled = true;
  G('inp').value = '';
  G('inp').style.height = 'auto';

  addMsg('user', msg);

  fetch('/route', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: msg})
  })
  .then(function(r) { return r.json(); })
  .then(function(rt) {
    cur = rt.agent || 'orchestrator';
    var a = AG[cur];
    G('hname').textContent = a.name;
    G('hdesc').textContent = a.desc;
    G('badge').textContent = cur === 'orchestrator' ? 'auto-routing' : cur;
    document.querySelectorAll('.ab').forEach(function(b) { b.classList.remove('on'); });
    var aBtn = G('ab-' + cur);
    if (aBtn) aBtn.classList.add('on');

    var bbl = addMsg('agent', '');
    var crsr = document.createElement('span');
    crsr.className = 'cur';
    bbl.appendChild(crsr);

    var full = '';
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/chat', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    var lastLen = 0;

    xhr.onprogress = function() {
      var chunk = xhr.responseText.slice(lastLen);
      lastLen = xhr.responseText.length;
      var lines = chunk.split('\n');
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line.startsWith('data:')) continue;
        try {
          var d = JSON.parse(line.slice(5).trim());
          if (d.t !== undefined) {
            full += d.t;
            bbl.innerHTML = renderMD(full);
            bbl.appendChild(crsr);
            G('msgs').scrollTop = 99999;
          }
          if (d.done) {
            crsr.remove();
            bbl.innerHTML = renderMD(full) || '(sin respuesta)';
            busy = false;
            G('sbtn').disabled = false;
          }
        } catch(e) {}
      }
    };

    xhr.onload = function() {
      crsr.remove();
      if (!full) bbl.textContent = '(sin respuesta del servidor)';
      busy = false;
      G('sbtn').disabled = false;
    };

    xhr.onerror = function() {
      crsr.remove();
      bbl.textContent = 'Error de conexion';
      busy = false;
      G('sbtn').disabled = false;
    };

    xhr.send(JSON.stringify({session_id: sid, message: msg, agent: cur}));
  })
  .catch(function(e) {
    addMsg('agent', 'Error: ' + e.message);
    busy = false;
    G('sbtn').disabled = false;
  });
}

G('sbtn').addEventListener('click', doSend);
G('inp').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); }
});
G('inp').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

})();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return PAGE

@app.route("/health")
def health():
    return jsonify({"ok":True,"api_key":bool(os.environ.get("ANTHROPIC_API_KEY"))})

@app.route("/route", methods=["POST"])
def route_api():
    d = request.get_json() or {}
    ag = route_msg(d.get("message",""))
    return jsonify({"agent":ag,"name":AGENTS[ag]["name"]})

@app.route("/session/<sid>/clear", methods=["POST"])
def clear_session(sid):
    if sid in sessions: sessions[sid]["history"] = []
    return jsonify({"ok":True})

@app.route("/chat", methods=["POST"])
def chat():
    d = request.get_json() or {}
    sid = d.get("session_id","x")
    msg = d.get("message","")
    akey = d.get("agent") or route_msg(msg)
    agent = AGENTS.get(akey, AGENTS["orchestrator"])
    session = get_session(sid)
    history = session["history"][-16:]

    def gen():
        api_key = os.environ.get("ANTHROPIC_API_KEY","")
        if not HAS_ANTHROPIC or not api_key:
            text = "[" + agent["name"] + " - Demo]\n\nConfigura ANTHROPIC_API_KEY en Railway.\n\nMensaje: " + msg[:80]
            for ch in text:
                yield "data: " + json.dumps({"t": ch}) + "\n\n"
                time.sleep(0.01)
            yield "data: " + json.dumps({"done": True}) + "\n\n"
            return
        try:
            client = anthropic.Anthropic(api_key=api_key)
            full = ""
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=agent["system"],
                messages=list(history) + [{"role":"user","content":msg}]
            ) as s:
                for t in s.text_stream:
                    full += t
                    yield "data: " + json.dumps({"t": t}) + "\n\n"
            session["history"] += [
                {"role":"user","content":msg},
                {"role":"assistant","content":full}
            ]
            yield "data: " + json.dumps({"done": True}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"t": "Error: " + str(e)[:100]}) + "\n\n"
            yield "data: " + json.dumps({"done": True}) + "\n\n"

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

if __name__ == "__main__":
    print("phi47 Agent Chat | port=" + str(PORT))
    print("API: " + ("OK" if os.environ.get("ANTHROPIC_API_KEY") else "NOT SET - demo mode"))
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
