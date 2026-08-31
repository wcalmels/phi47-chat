# ⬡ phi47 Agent Chat

**Interfaz web para los 10 agentes especializados phi47-OS**

Chat tipo Claude pero con agentes que conocen profundamente
Colmena, Colmente, Nemosine, Cyber-Sentinel, HAV-Engine y más.

---

## Deploy en Railway (3 minutos)

1. Fork este repo en GitHub
2. Conectar a [Railway](https://railway.app)
3. Agregar variable de entorno: `ANTHROPIC_API_KEY=sk-ant-...`
4. Deploy automático → URL pública lista

---

## Local (1 minuto)

```bash
pip install flask flask-cors anthropic gunicorn
export ANTHROPIC_API_KEY=sk-ant-...
python app.py
# → http://localhost:7047
```

---

## Los 10 agentes

| Emoji | Agente | Especialidad |
|-------|--------|-------------|
| 🎯 | Orchestrator | Coordina, prioriza, aprueba |
| 🏗️ | Architect | Specs, interfaces, decisiones técnicas |
| ⬡ | Colmena-Dev | OS auto-constructivo (L1-L25) |
| 🧠 | Colmente-Dev | IIT + agentes + multi-agente |
| 🛡️ | CyberGuard-Dev | Sentinel: TDA, FPR=0.45% |
| 🧬 | Nemosine-Dev | Memoria: SQLite, Welford, EMA |
| ⚙️ | TCW-SCM-Dev | Validación cruzada |
| 🔍 | HAV-Dev | Anti-alucinaciones, multi-LLM |
| ✅ | QA-phi47 | Tests, seed=42, CI |
| 📚 | Docs-phi47 | Papers, READMEs, pitch decks |

---

## Auto-routing

El sistema detecta el agente correcto desde tu mensaje:

```
"Cómo construyo L26 en Colmena"    → ⬡ Colmena-Dev
"Fix FPR en el ensemble detector"   → 🛡️ CyberGuard-Dev
"Escribe tests para Nemosine EMA"   → ✅ QA-phi47
"Diseña la interfaz de L3 grounding"→ 🏗️ Architect
"Actualiza README de HAV-Engine"    → 📚 Docs-phi47
```

También podés seleccionar el agente manualmente desde el sidebar.

---

## API

```bash
POST /chat           # stream SSE
POST /route          # auto-detect agent
GET  /agents         # list all agents
GET  /health         # status
```

---

## Flujo con Cursor

1. Describís la tarea en el chat
2. El agente responde con código en formato `FILE:` / `TERMINAL:`
3. Copiás en Cursor
4. Cursor implementa el código
5. QA-phi47 genera los tests

---

**Author:** Walter Calmels Von dem Knesebeck · TUCH Systems · phi47.cl
