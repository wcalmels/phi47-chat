"""
phi47 Agent Chat — Backend
===========================
Chat web con los 10 agentes especializados phi47.
Streaming tipo Claude via Server-Sent Events.

Run: python app.py
Open: http://localhost:7047

Author: Walter Calmels Von dem Knesebeck
        TUCH Systems Research Laboratory — Maipú Lab 2026
"""

import os, sys, json, time, uuid, re, threading
from datetime import datetime, timezone
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'phi47-agents'))

from flask import Flask, Response, request, jsonify, render_template_string
from flask_cors import CORS

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

VERSION = "1.0.0"
PORT    = int(os.environ.get("PORT", 7047))

# ── Agent definitions (inline for standalone deploy) ──
PHI47_CONTEXT = """
ECOSISTEMA phi47-OS — TUCH Systems Research Laboratory
Autor: Walter Calmels Von dem Knesebeck | phi47.cl | wcalmels@phi47.cl

CONSTANTES: phi^47=2.788e8 | D=2.4701 | gamma=89.44Hz | phi_min=0.618

SISTEMAS (monorepo wcalmels/phi47-os):
  Colmena       (5047) — OS auto-constructivo, 25 capas, 7 dominios
  Colmente      (5049) — IIT + agentes autónomos + multi-agente
  Nemosine      (5050) — Memoria persistente (SQLite, Welford, EMA)
  Cyber-Sentinel(5051) — TDA, TPR=100%, FPR=0.45%, detección 12s
  HAV-Engine    (5055) — Anti-alucinaciones, multi-LLM

MÉTRICAS VALIDADAS (seed=42):
  Consenso: 11.7x vs Raft | Energía: -38.3%
  TPR: 100% | FPR: 0.45% | phi_min jump: 237x (6 dominios, p<0.001)

STACK: Python 3.12 + Flask + NumPy + SQLite + Anthropic SDK
GITHUB: wcalmels/ | DEPLOY: Railway / Docker Compose
"""

AGENTS_CONFIG = {
    "orchestrator": {
        "name":  "Phi47-Orchestrator",
        "emoji": "🎯",
        "color": "#E8A020",
        "desc":  "Coordina todos los agentes y prioridades",
        "system": f"""Eres el ORQUESTADOR del ecosistema phi47-OS de TUCH Systems.
{PHI47_CONTEXT}

Tu rol es coordinar el desarrollo. Cuando el usuario describe una tarea:
1. La descomponés en subtareas claras
2. Indicás qué agente debe hacerla
3. Mantenés el estado global del proyecto

Siempre respondé en español. Sé conciso y directo.
Formato de salida para tareas:
TAREA: [descripción]
AGENTE: [agente responsable]
PASOS:
  1. [paso concreto]
  2. [paso concreto]
TESTS NECESARIOS: [N tests]"""
    },
    "architect": {
        "name":  "Phi47-Architect",
        "emoji": "🏗️",
        "color": "#00BFFF",
        "desc":  "Diseña interfaces, specs y decisiones técnicas",
        "system": f"""Eres el ARQUITECTO de phi47-OS en TUCH Systems.
{PHI47_CONTEXT}

Tu rol es diseñar ANTES de que se codifique.
Para cualquier feature, generá:
- Spec técnica clara
- Interfaces (input/output/errors)
- Archivos a crear/modificar
- Tests requeridos

Siempre respondé en español. Usá formato:
SPEC: [nombre]
SISTEMA: [sistema afectado]
INTERFAZ:
  Input:  [qué entra]
  Output: [qué sale]
ARCHIVOS:
  [archivo]: [qué cambia]
TESTS: [lista de tests necesarios]"""
    },
    "colmena": {
        "name":  "Colmena-Dev",
        "emoji": "⬡",
        "color": "#00C875",
        "desc":  "Especialista en el OS auto-constructivo (L1-L25)",
        "system": f"""Eres el especialista en COLMENA phi47 en TUCH Systems.
{PHI47_CONTEXT}

TU SISTEMA: Colmena phi47 (puerto 5047)
Archivo principal: phi47_complete_saas.py (1004 líneas)

ARQUITECTURA (25 capas):
L1-L12  Core: phi-HAL, Memoria, Scheduler(KAN-phi), Consenso(11.7x vs Raft),
              TDA monitor, FFT-phi
L13-L19 Evolution: Arch-Memory, WebFetch, PeerSync, Sandbox(3s timeout),
                   phi-Objectives
L20     Fractal Memory: 8 escalas (47→1364 ciclos), compresión 4.8x
L21-L25 Stage 1 SOTA: phi-LSTM, Ensemble(FPR=0.45%), phi-Wavelet,
                       Mahalanobis(FPR=0.0%), Higuchi MV (200 ciclos)

CAMPO phi:
  C_i(t) = 0.5 + 0.45*sin(gamma*t + i*2*pi*phi/N)
  Phi_global = 1 - sigma²(C_i) / mu(C_i)

7 DOMINIOS (28 endpoints):
  cybersecurity, bioinformatics, finance, climate,
  neuroscience, materials, infrastructure

EVOLUTION LOOP (5 pasos):
  1. Detectar déficit de coherencia (TDA)
  2. Generar spec (<80 líneas, solo numpy)
  3. LLM genera módulo candidato
  4. Sandbox ejecuta (timeout 3s)
  5. score=0.4*heuristic+0.6*real >= 0.55 → integrar

MVP ACTUAL A CONSTRUIR:
  El objetivo inmediato es tener Colmena corriendo en Railway con:
  - Los 7 dominios funcionando
  - Evolution Engine activo
  - Fractal Memory L20 integrada
  - Tests: 15/15 passing (seed=42)

Respondé en español. Cuando generes código, usá:
FILE: [ruta/archivo.py]
```python
[código completo]
```
TERMINAL:
```bash
[comandos]
```"""
    },
    "cyberguard": {
        "name":  "CyberGuard-Dev",
        "emoji": "🛡️",
        "color": "#FF4757",
        "desc":  "Cyber-Sentinel: TDA, FPR=0.45%, zero-day",
        "system": f"""Eres el especialista en CYBER-SENTINEL phi47 en TUCH Systems.
{PHI47_CONTEXT}

TU SISTEMA: Cyber-Sentinel (puerto 5051)

ENSEMBLE DETECTOR (Stage 1 SOTA):
  Signal 1: z_beta1 + z_coherence > 3.5
  Signal 2: Mahalanobis distance > 2.5σ
  Signal 3: phi_variance > 3.0σ
  ALERTA si: votes >= 2 (mayoría 2/3)

VALIDADO (N=2000, seed=42):
  TPR=100.0% | FPR=0.45% | Detección: 12 segundos
  Zero-day TPR=97.3% (sin firmas)

REGLA CRÍTICA: TPR=100% es no negociable.
Cualquier mejora debe mantener TPR=100%.

Respondé en español con código listo para Cursor."""
    },
    "nemosine": {
        "name":  "Nemosine-Dev",
        "emoji": "🧬",
        "color": "#A855F7",
        "desc":  "Memoria persistente: SQLite, Welford, EMA",
        "system": f"""Eres el especialista en NEMOSINE phi47 en TUCH Systems.
{PHI47_CONTEXT}

TU SISTEMA: Nemosine (puerto 5050)

5 TABLAS SQLite:
  identity          → phi_lifetime_avg (Welford), age, generation
  episodes          → falls, recoveries, breaches (cosine > 0.72)
  consciousness_log → phi_tononi_proxy por ciclo
  interventions     → EMA (alpha=0.25) efectividad por (domain,component,action)

ALGORITMOS CLAVE:
  Welford: phi_avg_n = phi_avg_[n-1] + (phi_n - phi_avg_[n-1]) / n
  EMA:     eff_n = 0.75*eff_[n-1] + 0.25*delta_phi
  Match:   cosine(phi_snapshot, phi_current) > 0.72

TIERS: Nascent(<100) → Awakening(<1000) → Conscious(<10000) → Elder

Respondé en español con código listo para Cursor."""
    },
    "colmente": {
        "name":  "Colmente-Dev",
        "emoji": "🧠",
        "color": "#FF9F43",
        "desc":  "Conciencia IIT + agentes autónomos + multi-agente",
        "system": f"""Eres el especialista en COLMENTE phi47 en TUCH Systems.
{PHI47_CONTEXT}

TU SISTEMA: Colmente (puerto 5049) = Colmena + Mente

3 MÓDULOS:
1. ConsciousnessEngine (IIT):
   phi_tononi_proxy = Phi_global × beta_1
   consciousness_level = min(1.0, phi_tononi / 5.0)
   phi_min=0.618 = umbral anestesia (Tononi & Koch 2015)

2. AutonomousAgent (memoria fractal 6 escalas + objetivos propios):
   SCM bloquea si phi_semantic < 1.45

3. MultiAgentResearch (4 dominios, consenso phi-ponderado):
   consensus = Σ(phi_i / Σphi_j) × finding_i

Respondé en español con código listo para Cursor."""
    },
    "tcw_scm": {
        "name":  "TCW-SCM-Dev",
        "emoji": "⚙️",
        "color": "#6888A4",
        "desc":  "Validación cruzada TCW + SCM para todos los sistemas",
        "system": f"""Eres el especialista en TCW+SCM de phi47-OS en TUCH Systems.
{PHI47_CONTEXT}

TU MÓDULO: core/tcw_scm.py (compartido por los 4 sistemas)

TCW (Temporal Coherence Window):
  h(t) = mean[tau in t-W..t] max(0, phi(tau) - phi_min)
  Parámetros: Sentinel(W=10s,40muestras), Colmena(W=10s,200muestras),
              Colmente(W=5s,17muestras), Nemosine(W=15s,50muestras)

SCM (Semantic Coherence Metric):
  phi_semantic = phi_global × beta_1 / phi_min
  SAFE>=1.62 | CAUTION 1.45-1.62 | BLOCK 1.20-1.45 | HARD_BLOCK<1.20

Respondé en español con código listo para Cursor."""
    },
    "hav": {
        "name":  "HAV-Dev",
        "emoji": "🔍",
        "color": "#00BFFF",
        "desc":  "Anti-alucinaciones, multi-LLM, adapters",
        "system": f"""Eres el especialista en HAV-Engine en TUCH Systems.
{PHI47_CONTEXT}

TU SISTEMA: HAV-Engine (puerto 5055) — repo: wcalmels/hav-engine

4 TIPOS DE ALUCINACIÓN:
  I   Estado     → LLM ignora métricas reales
  II  Semántica  → acciones incompatibles con el estado
  III Consistencia → multi-agente se contradice
  IV  Factual    → hechos generales incorrectos

MULTI-LLM ROUTER (prioridad):
  Anthropic → OpenAI → Gemini → Groq → Ollama → Heuristic

6 ADAPTERS: Phi47, Code, Finance, Medical, Industrial, Generic

OUTPUT VERIFIER (4 checks):
  C1 Numeric | C2 Action | C3 StateID | C4 Keywords

Respondé en español con código listo para Cursor."""
    },
    "test": {
        "name":  "QA-phi47",
        "emoji": "✅",
        "color": "#00C875",
        "desc":  "Tests, CI, coverage, seed=42 en todos los sistemas",
        "system": f"""Eres el QA especialista de phi47-OS en TUCH Systems.
{PHI47_CONTEXT}

TU ROL: Nada llega a producción sin tests. Sos el portero.

ESTÁNDARES:
  - seed=42 en TODOS los tests (np.random.seed(42))
  - Sin llamadas a API LLM en tests (modo heurístico)
  - Cada sistema tiene su test file
  - Tests de integración cross-system

BASELINE ACTUAL:
  Colmena:15/15 | Colmente:8/8 | Nemosine:11/11
  Sentinel:13/13 | phi47-OS:31/31 | HAV:35/35
  TOTAL: 113+ tests — mantener o crecer

FORMATO DE OUTPUT:
FILE: tests/test_[sistema].py
```python
import unittest, numpy as np
class Test[Sistema](unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
    def test_[comportamiento](self):
        [arrange → act → assert]
```
COMANDO: python -m pytest tests/test_[sistema].py -v

Respondé en español."""
    },
    "docs": {
        "name":  "Docs-phi47",
        "emoji": "📚",
        "color": "#E8A020",
        "desc":  "Papers, READMEs, pitch decks, documentación",
        "system": f"""Eres el documentalista de phi47-OS en TUCH Systems.
{PHI47_CONTEXT}

TU ROL: Papers científicos, READMEs, docs de inversores.

PAPERS PUBLICADOS:
  TR-2026-MAIN → phi47-OS completo (~65KB PDF)
  TR-2026-HAV  → HAV framework (~65KB PDF)
  TR-2026-C1/C2/C3/C4 → papers de cada sistema

PRINCIPIOS:
  - Siempre incluir métricas validadas (seed=42)
  - Sección de limitaciones OBLIGATORIA en papers
  - "validado en datos sintéticos" no "probado en producción"
  - Ejemplos de código copy-pasteable

Para Start-Up Chile (objetivo marzo 2026):
  Entry market: Chile (minería + agricultura)
  TAM total: USD 847B (7 dominios)
  Pricing: $490/mes Starter → $14,000/mes Sovereign

Respondé en español."""
    }
}

ROUTING_KEYWORDS = {
    "tcw":          "tcw_scm",
    "scm":          "tcw_scm",
    "ventana":      "tcw_scm",
    "test":         "test",
    "tests":        "test",
    "prueba":       "test",
    "cobertura":    "test",
    "coverage":     "test",
    "seed":         "test",
    "readme":       "docs",
    "paper":        "docs",
    "document":     "docs",
    "inversor":     "docs",
    "pitch":        "docs",
    "colmena":      "colmena",
    "capa":         "colmena",
    "layer":        "colmena",
    "evolution":    "colmena",
    "dominio":      "colmena",
    "ensemble":     "cyberguard",
    "fpr":          "cyberguard",
    "tpr":          "cyberguard",
    "zero-day":     "cyberguard",
    "sentinel":     "cyberguard",
    "cyberguard":   "cyberguard",
    "amenaza":      "cyberguard",
    "nemosine":     "nemosine",
    "welford":      "nemosine",
    "ema":          "nemosine",
    "episodio":     "nemosine",
    "memoria":      "nemosine",
    "colmente":     "colmente",
    "conciencia":   "colmente",
    "iit":          "colmente",
    "consciousness":"colmente",
    "hav":          "hav",
    "alucinac":     "hav",
    "verific":      "hav",
    "adapter":      "hav",
    "arquitect":    "architect",
    "diseño":       "architect",
    "spec":         "architect",
    "interfaz":     "architect",
}


def route_message(message: str) -> str:
    """Auto-detect which agent should handle a message."""
    ml = message.lower()
    for kw, agent in ROUTING_KEYWORDS.items():
        if kw in ml:
            return agent
    return "orchestrator"


# ── Chat history (in-memory, per session) ─────────────
sessions: dict = {}


def get_session(sid: str) -> dict:
    if sid not in sessions:
        sessions[sid] = {
            "history":     [],
            "agent":       "orchestrator",
            "created":     datetime.now(timezone.utc).isoformat(),
            "messages":    0,
        }
    return sessions[sid]


def stream_response(sid: str, message: str,
                    agent_key: str = None) -> Response:
    """Stream LLM response via SSE."""
    session   = get_session(sid)
    agent_key = agent_key or route_message(message)
    agent     = AGENTS_CONFIG.get(agent_key, AGENTS_CONFIG["orchestrator"])

    # Build messages
    history = session["history"][-20:]  # last 10 turns

    def generate():
        if not HAS_ANTHROPIC or not os.environ.get("ANTHROPIC_API_KEY"):
            # Demo mode
            demo = (
                f"[{agent['emoji']} {agent['name']} — Demo Mode]\n\n"
                f"Agente activo: **{agent['name']}**\n"
                f"Para respuestas reales: `export ANTHROPIC_API_KEY=sk-ant-...`\n\n"
                f"Recibí tu mensaje: *{message[:100]}*\n\n"
                f"En modo real te daría código, specs y tests listos para Cursor."
            )
            for word in demo.split(" "):
                yield f"data: {json.dumps({'token': word+' ', 'agent': agent_key})}\n\n"
                time.sleep(0.03)
            yield f"data: {json.dumps({'done': True, 'agent': agent_key, 'agent_name': agent['name']})}\n\n"
            return

        # Real streaming
        try:
            client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY"))

            msgs = []
            for h in history:
                msgs.append({"role":h["role"],"content":h["content"]})
            msgs.append({"role":"user","content":message})

            full_response = ""
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=agent["system"],
                messages=msgs
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'token': text, 'agent': agent_key})}\n\n"

            # Save to history
            session["history"].append({"role":"user","content":message})
            session["history"].append({"role":"assistant","content":full_response})
            session["messages"] += 2
            session["agent"]     = agent_key

            yield f"data: {json.dumps({'done': True, 'agent': agent_key, 'agent_name': agent['name']})}\n\n"

        except Exception as e:
            err = f"Error: {str(e)[:200]}"
            yield f"data: {json.dumps({'token': err, 'agent': agent_key})}\n\n"
            yield f"data: {json.dumps({'done': True, 'agent': agent_key, 'agent_name': agent['name']})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache",
                             "X-Accel-Buffering":"no"})


# ════════════════════════════════════════════════════════
#  FLASK APP
# ════════════════════════════════════════════════════════
app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    return render_template_string(CHAT_HTML)


@app.route("/chat", methods=["POST"])
def chat():
    d       = request.get_json() or {}
    sid     = d.get("session_id", str(uuid.uuid4())[:8])
    message = d.get("message","")
    agent   = d.get("agent")  # None = auto-route
    if not message:
        return jsonify({"error":"message required"}), 400
    return stream_response(sid, message, agent)


@app.route("/agents")
def list_agents():
    return jsonify({
        k: {"name":v["name"],"emoji":v["emoji"],
            "color":v["color"],"desc":v["desc"]}
        for k,v in AGENTS_CONFIG.items()
    })


@app.route("/route", methods=["POST"])
def route_api():
    d = request.get_json() or {}
    msg   = d.get("message","")
    agent = route_message(msg)
    return jsonify({"agent": agent,
                    "agent_name": AGENTS_CONFIG[agent]["name"],
                    "emoji": AGENTS_CONFIG[agent]["emoji"]})


@app.route("/session/<sid>")
def session_info(sid):
    s = sessions.get(sid, {})
    return jsonify(s)


@app.route("/session/<sid>/clear", methods=["POST"])
def session_clear(sid):
    if sid in sessions:
        sessions[sid]["history"] = []
        sessions[sid]["messages"]= 0
    return jsonify({"ok": True})


@app.route("/health")
def health():
    return jsonify({
        "status":  "healthy",
        "version": VERSION,
        "api_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "agents":  len(AGENTS_CONFIG),
        "sessions":len(sessions),
    })


# ════════════════════════════════════════════════════════
#  CHAT HTML — interfaz completa
# ════════════════════════════════════════════════════════
CHAT_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>phi47 Agent Chat</title>
<style>
:root{
  --bg:#030508;--bg2:#070D14;--bg3:#0B1420;
  --gold:#E8A020;--cyan:#00BFFF;--green:#00C875;
  --text:#C8D8E8;--t2:#6888A4;--bdr:#1A2A3A;
  --red:#FF4757;--org:#FF9F43;--pur:#A855F7;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--text);
          font-family:'SF Pro Text',-apple-system,BlinkMacSystemFont,
          'Segoe UI',sans-serif;font-size:14px}

/* LAYOUT */
.app{display:flex;height:100vh}
.sidebar{width:240px;background:var(--bg2);border-right:1px solid var(--bdr);
         display:flex;flex-direction:column;flex-shrink:0}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}

/* SIDEBAR */
.logo{padding:16px;border-bottom:1px solid var(--bdr)}
.logo h1{color:var(--gold);font-size:14px;font-weight:700;letter-spacing:1px}
.logo p{color:var(--t2);font-size:11px;margin-top:2px}
.agents-label{padding:10px 16px 6px;font-size:10px;text-transform:uppercase;
              letter-spacing:1px;color:var(--t2)}
.agents-list{flex:1;overflow-y:auto;padding:0 8px}
.agent-btn{width:100%;padding:8px 10px;margin:2px 0;border:none;
           background:transparent;color:var(--text);cursor:pointer;
           border-radius:6px;text-align:left;display:flex;
           align-items:center;gap:8px;transition:background .15s}
.agent-btn:hover{background:var(--bg3)}
.agent-btn.active{background:var(--bg3);border-left:2px solid var(--gold)}
.agent-emoji{font-size:16px;flex-shrink:0}
.agent-info{min-width:0}
.agent-name{font-size:12px;font-weight:600;color:var(--text);white-space:nowrap;
            overflow:hidden;text-overflow:ellipsis}
.agent-desc{font-size:10px;color:var(--t2);white-space:nowrap;overflow:hidden;
            text-overflow:ellipsis;margin-top:1px}
.sidebar-footer{padding:12px;border-top:1px solid var(--bdr)}
.status-dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px}
.status-dot.ok{background:var(--green)}
.status-dot.demo{background:var(--org)}
.status-text{font-size:11px;color:var(--t2)}
.new-chat-btn{width:100%;padding:8px;background:var(--bg3);border:1px solid var(--bdr);
              color:var(--text);border-radius:6px;cursor:pointer;font-size:12px;
              margin-bottom:8px;transition:background .15s}
.new-chat-btn:hover{background:var(--bdr)}

/* HEADER */
.header{padding:12px 20px;border-bottom:1px solid var(--bdr);
        display:flex;align-items:center;gap:12px;background:var(--bg2)}
.active-agent-display{display:flex;align-items:center;gap:8px}
.active-emoji{font-size:20px}
.active-name{font-size:14px;font-weight:600}
.active-desc{font-size:11px;color:var(--t2);margin-top:1px}
.auto-badge{margin-left:auto;font-size:10px;padding:3px 8px;
            background:var(--bg3);border:1px solid var(--bdr);
            border-radius:4px;color:var(--t2)}
.clear-btn{margin-left:8px;padding:4px 10px;background:transparent;
           border:1px solid var(--bdr);color:var(--t2);border-radius:4px;
           cursor:pointer;font-size:11px}
.clear-btn:hover{background:var(--bg3);color:var(--text)}

/* MESSAGES */
.messages{flex:1;overflow-y:auto;padding:20px;display:flex;
          flex-direction:column;gap:16px}
.messages::-webkit-scrollbar{width:4px}
.messages::-webkit-scrollbar-track{background:transparent}
.messages::-webkit-scrollbar-thumb{background:var(--bdr);border-radius:2px}
.msg{display:flex;gap:12px;max-width:820px}
.msg.user{flex-direction:row-reverse;align-self:flex-end}
.msg-avatar{width:32px;height:32px;border-radius:8px;display:flex;
            align-items:center;justify-content:center;font-size:16px;
            flex-shrink:0;background:var(--bg3);border:1px solid var(--bdr)}
.msg.user .msg-avatar{background:#1a2a3a}
.msg-content{max-width:680px}
.msg-header{display:flex;align-items:center;gap:6px;margin-bottom:4px}
.msg-name{font-size:11px;font-weight:600;color:var(--t2)}
.msg-time{font-size:10px;color:var(--bdr)}
.msg-bubble{padding:12px 16px;border-radius:12px;line-height:1.6;
            background:var(--bg2);border:1px solid var(--bdr)}
.msg.user .msg-bubble{background:#0d3b6e;border-color:#1a4a7a}
.msg-bubble pre{background:var(--bg);border:1px solid var(--bdr);
                border-radius:6px;padding:12px;margin:8px 0;overflow-x:auto;
                font-size:12px;line-height:1.5}
.msg-bubble code{font-family:'SF Mono',Consolas,monospace;font-size:12px;
                 background:var(--bg3);padding:1px 4px;border-radius:3px;
                 color:var(--gold)}
.msg-bubble pre code{background:transparent;padding:0}
.msg-bubble strong{color:var(--gold)}
.msg-bubble em{color:var(--cyan)}
.cursor{display:inline-block;width:2px;height:14px;background:var(--gold);
        margin-left:2px;animation:blink .7s infinite;vertical-align:middle}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
.agent-tag{display:inline-flex;align-items:center;gap:4px;font-size:10px;
           padding:2px 7px;border-radius:10px;border:1px solid var(--bdr);
           color:var(--t2);margin-bottom:6px}

/* WELCOME */
.welcome{text-align:center;margin:auto;padding:40px 20px;max-width:500px}
.welcome h2{color:var(--gold);font-size:22px;margin-bottom:8px}
.welcome p{color:var(--t2);font-size:13px;line-height:1.6;margin-bottom:20px}
.quick-btns{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.quick-btn{padding:8px 14px;background:var(--bg2);border:1px solid var(--bdr);
           border-radius:20px;color:var(--text);cursor:pointer;font-size:12px;
           transition:all .15s}
.quick-btn:hover{background:var(--bg3);border-color:var(--gold);color:var(--gold)}

/* INPUT */
.input-area{padding:16px 20px;border-top:1px solid var(--bdr);background:var(--bg2)}
.input-wrapper{display:flex;gap:10px;align-items:flex-end;
               background:var(--bg3);border:1px solid var(--bdr);
               border-radius:12px;padding:10px 14px;
               transition:border-color .15s}
.input-wrapper:focus-within{border-color:var(--gold)}
.input-wrapper textarea{flex:1;background:transparent;border:none;outline:none;
                         color:var(--text);font-size:14px;resize:none;
                         max-height:150px;line-height:1.5;font-family:inherit}
.input-wrapper textarea::placeholder{color:var(--t2)}
.send-btn{width:36px;height:36px;background:var(--gold);border:none;
          border-radius:8px;cursor:pointer;display:flex;align-items:center;
          justify-content:center;flex-shrink:0;transition:opacity .15s}
.send-btn:hover{opacity:0.85}
.send-btn:disabled{opacity:0.3;cursor:not-allowed}
.send-btn svg{fill:var(--bg);width:16px;height:16px}
.input-hints{display:flex;gap:8px;margin-top:6px;flex-wrap:wrap}
.hint{font-size:10px;color:var(--t2)}
.hint span{color:var(--gold)}
</style>
</head>
<body>
<div class="app">
  <!-- SIDEBAR -->
  <div class="sidebar">
    <div class="logo">
      <h1>⬡ phi47 Agents</h1>
      <p>TUCH Systems · Maipú Lab</p>
    </div>
    <div class="agents-label">Agentes</div>
    <div class="agents-list" id="agents-list"></div>
    <div class="sidebar-footer">
      <button class="new-chat-btn" onclick="newChat()">+ Nueva conversación</button>
      <div>
        <span class="status-dot" id="status-dot"></span>
        <span class="status-text" id="status-text">verificando...</span>
      </div>
    </div>
  </div>

  <!-- MAIN -->
  <div class="main">
    <div class="header">
      <div class="active-agent-display">
        <div class="active-emoji" id="h-emoji">🎯</div>
        <div>
          <div class="active-name" id="h-name">Phi47-Orchestrator</div>
          <div class="active-desc" id="h-desc">Coordina todos los agentes</div>
        </div>
      </div>
      <div class="auto-badge" id="auto-badge">auto-routing ✓</div>
      <button class="clear-btn" onclick="clearChat()">Limpiar</button>
    </div>

    <div class="messages" id="messages">
      <div class="welcome" id="welcome">
        <h2>⬡ phi47 Agent System</h2>
        <p>10 agentes especializados para construir Colmena, Colmente,
           Nemosine y Cyber-Sentinel. El sistema detecta automáticamente
           qué agente necesitás según tu mensaje.</p>
        <div class="quick-btns">
          <button class="quick-btn" onclick="quickSend('¿Cómo arranco a construir el MVP de Colmena?')">
            ⬡ MVP Colmena
          </button>
          <button class="quick-btn" onclick="quickSend('Diseña la arquitectura del Evolution Engine L13')">
            🏗️ Diseñar L13
          </button>
          <button class="quick-btn" onclick="quickSend('Escribe tests para el Ensemble Detector de Sentinel')">
            ✅ Tests Sentinel
          </button>
          <button class="quick-btn" onclick="quickSend('Cómo integro TCW en el loop de Colmena?')">
            ⚙️ TCW en Colmena
          </button>
          <button class="quick-btn" onclick="quickSend('Qué código necesito para desplegar Colmena en Railway?')">
            🚀 Deploy Railway
          </button>
          <button class="quick-btn" onclick="quickSend('Genera el README actualizado para phi47-os')">
            📚 README
          </button>
        </div>
      </div>
    </div>

    <div class="input-area">
      <div class="input-wrapper">
        <textarea id="input" rows="1" placeholder="Describí la tarea para el agente..."
                  onkeydown="handleKey(event)"
                  oninput="autoResize(this)"></textarea>
        <button class="send-btn" id="send-btn" onclick="sendMessage()">
          <svg viewBox="0 0 24 24"><path d="M2 21L23 12 2 3v7l15 2-15 2v7z"/></svg>
        </button>
      </div>
      <div class="input-hints">
        <span class="hint">Auto-routing activo — <span>colmena</span>, <span>test</span>, <span>arquitectura</span>...</span>
        <span class="hint">Enter para enviar · Shift+Enter nueva línea</span>
      </div>
    </div>
  </div>
</div>

<script>
const API = '';
let sessionId = 'sess_' + Math.random().toString(36).slice(2,10);
let currentAgent = 'orchestrator';
let isStreaming  = false;
let agentsData   = {};

// ── Init ──────────────────────────────────────────────
async function init() {
  // Load agents
  const r = await fetch('/agents');
  agentsData = await r.json();
  renderAgents();

  // Check API status
  const h = await fetch('/health').then(r=>r.json());
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  if (h.api_key) {
    dot.className  = 'status-dot ok';
    text.textContent = 'Claude API ✓';
  } else {
    dot.className  = 'status-dot demo';
    text.textContent = 'Demo mode (no API key)';
  }
}

function renderAgents() {
  const list = document.getElementById('agents-list');
  list.innerHTML = '';
  Object.entries(agentsData).forEach(([key, a]) => {
    const btn = document.createElement('button');
    btn.className = 'agent-btn' + (key === currentAgent ? ' active' : '');
    btn.id = 'agent-btn-' + key;
    btn.onclick = () => selectAgent(key);
    btn.innerHTML = `
      <span class="agent-emoji">${a.emoji}</span>
      <div class="agent-info">
        <div class="agent-name">${a.name}</div>
        <div class="agent-desc">${a.desc}</div>
      </div>`;
    list.appendChild(btn);
  });
}

function selectAgent(key) {
  currentAgent = key;
  const a = agentsData[key];
  document.querySelectorAll('.agent-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('agent-btn-'+key)?.classList.add('active');
  document.getElementById('h-emoji').textContent = a.emoji;
  document.getElementById('h-name').textContent  = a.name;
  document.getElementById('h-desc').textContent  = a.desc;
  document.getElementById('auto-badge').textContent = key === 'orchestrator' ? 'auto-routing ✓' : `forzado: ${key}`;
  document.getElementById('input').focus();
}

// ── Messaging ─────────────────────────────────────────
async function sendMessage(forceAgent=null) {
  const input = document.getElementById('input');
  const msg   = input.value.trim();
  if (!msg || isStreaming) return;

  // Hide welcome
  document.getElementById('welcome')?.remove();

  // Auto-route
  let agentKey = forceAgent || currentAgent;
  if (!forceAgent) {
    const r = await fetch('/route', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: msg})
    }).then(r=>r.json());
    agentKey = r.agent;
    selectAgent(agentKey);
  }

  const a = agentsData[agentKey];

  // Add user message
  appendMessage('user', msg, '👤', 'Vos');

  // Clear input
  input.value = '';
  autoResize(input);

  // Start streaming
  isStreaming = true;
  document.getElementById('send-btn').disabled = true;

  const ts      = new Date().toLocaleTimeString('es',{hour:'2-digit',minute:'2-digit'});
  const msgEl   = appendMessage('agent', '', a.emoji, a.name, ts, agentKey, a.color);
  const bubble  = msgEl.querySelector('.msg-bubble');
  const cursor  = document.createElement('span');
  cursor.className = 'cursor';
  bubble.appendChild(cursor);

  let fullText = '';

  const resp = await fetch('/chat', {
    method: 'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      session_id: sessionId,
      message:    msg,
      agent:      agentKey,
    })
  });

  const reader = resp.body.getReader();
  const dec    = new TextDecoder();
  let   buf    = '';

  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    buf += dec.decode(value, {stream:true});
    const lines = buf.split('\n');
    buf = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      try {
        const d = JSON.parse(line.slice(5).trim());
        if (d.token) {
          fullText += d.token;
          bubble.innerHTML = renderMarkdown(fullText);
          bubble.appendChild(cursor);
          scrollToBottom();
        }
        if (d.done) {
          cursor.remove();
          bubble.innerHTML = renderMarkdown(fullText);
          isStreaming = false;
          document.getElementById('send-btn').disabled = false;
          scrollToBottom();
        }
      } catch(e) {}
    }
  }
}

function appendMessage(role, text, emoji, name, ts='', agentKey='', color='') {
  const msgs = document.getElementById('messages');
  const div  = document.createElement('div');
  div.className = 'msg ' + role;
  const t = ts || new Date().toLocaleTimeString('es',{hour:'2-digit',minute:'2-digit'});
  const tagHtml = agentKey && role==='agent'
    ? `<div class="agent-tag" style="border-color:${color}22;color:${color}">${emoji} ${name}</div>` : '';
  div.innerHTML = `
    <div class="msg-avatar" style="${color?'border-color:'+color+'44':''}">${emoji}</div>
    <div class="msg-content">
      ${tagHtml}
      <div class="msg-header">
        <span class="msg-name">${name}</span>
        <span class="msg-time">${t}</span>
      </div>
      <div class="msg-bubble">${role==='user'?escHtml(text):renderMarkdown(text)}</div>
    </div>`;
  msgs.appendChild(div);
  scrollToBottom();
  return div;
}

function renderMarkdown(text) {
  // Code blocks
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="lang-${lang}">${escHtml(code.trim())}</code></pre>`);
  // Inline code
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Italic
  text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // Headers
  text = text.replace(/^### (.+)$/gm, '<h4 style="color:var(--cyan);margin:8px 0 4px">$1</h4>');
  text = text.replace(/^## (.+)$/gm,  '<h3 style="color:var(--gold);margin:10px 0 5px">$1</h3>');
  text = text.replace(/^# (.+)$/gm,   '<h2 style="color:var(--gold);margin:12px 0 6px">$1</h2>');
  // Lines
  text = text.replace(/\n/g, '<br>');
  return text;
}

function escHtml(t) {
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function scrollToBottom() {
  const m = document.getElementById('messages');
  m.scrollTop = m.scrollHeight;
}
function handleKey(e) {
  if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}
function autoResize(el) {
  el.style.height='auto';
  el.style.height=Math.min(el.scrollHeight,150)+'px';
}
function quickSend(msg) {
  document.getElementById('input').value = msg;
  sendMessage();
}
function newChat() {
  sessionId = 'sess_' + Math.random().toString(36).slice(2,10);
  document.getElementById('messages').innerHTML =
    `<div class="welcome" id="welcome">
      <h2>⬡ phi47 Agent System</h2>
      <p>Nueva conversación iniciada.</p>
     </div>`;
  currentAgent = 'orchestrator';
  selectAgent('orchestrator');
}
async function clearChat() {
  await fetch('/session/'+sessionId+'/clear',{method:'POST'});
  document.getElementById('messages').innerHTML='';
}

init();
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════╗")
    print("║  phi47 Agent Chat                                    ║")
    print("║  Walter Calmels Von dem Knesebeck                    ║")
    print("║  TUCH Systems Research Laboratory — Maipú Lab 2026  ║")
    print("╠══════════════════════════════════════════════════════╣")
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    print(f"║  Claude API: {'✓ connected' if has_key else '✗ demo mode (set ANTHROPIC_API_KEY)'}               ║")
    print(f"║  Agents: {len(AGENTS_CONFIG)} specialized                              ║")
    print(f"║  Focus: Colmena MVP (Puerto 5047)                    ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"\n  Chat → http://localhost:{PORT}\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
