from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import get_config

router = APIRouter(tags=["architecture"])


def _render(config) -> str:
    llm_active = config.llm.provider
    stt_active = config.voice.stt_model
    tts_active = config.voice.tts_model
    rag_active = config.rag.store
    db_active = config.database.url
    auth_on = "ON" if config.auth.enabled else "OFF"
    rag_on = "ON" if config.rag.enabled else "OFF"
    voice_on = "ON" if config.voice.enabled else "OFF"
    enabled_tools = ", ".join(config.tools.enabled) or "—"

    def pill(label: str, active: bool, sub: str = "") -> str:
        cls = "pill active" if active else "pill"
        sub_html = f"<span class='sub'>{sub}</span>" if sub else ""
        return f"<div class='{cls}'><span class='dot'></span><span class='lbl'>{label}</span>{sub_html}</div>"

    llm_pills = "".join(
        [
            pill("ollama", llm_active == "ollama", "qwen2.5:3b · local"),
            pill("openai", llm_active == "openai", "gpt-4o · cloud"),
            pill("anthropic", llm_active == "anthropic", "claude-sonnet-4 · cloud"),
            pill("bedrock", llm_active == "bedrock", "AWS · cloud"),
            pill("groq", llm_active == "groq", "llama-3.3-70b · cloud"),
        ]
    )
    stt_pills = "".join(
        [
            pill("distil-whisper", stt_active == "distil-whisper", "fastrtc · local"),
            pill(
                "faster-whisper",
                stt_active in ("faster-whisper", "faster_whisper"),
                "CTranslate2 · local",
            ),
        ]
    )
    tts_pills = "".join(
        [
            pill("piper", tts_active == "piper", "ONNX · local"),
            pill("kokoro", tts_active == "kokoro", "fastrtc · local"),
            pill("chattts", tts_active == "chattts", "expressive · local"),
            pill("edge", tts_active == "edge", "Microsoft · cloud"),
            pill("groq", tts_active == "groq", "PlayAI · cloud"),
        ]
    )
    rag_pills = "".join(
        [
            pill("faiss", rag_active == "faiss", "local index"),
            pill("chromadb", rag_active == "chromadb", "service"),
            pill("opensearch", rag_active == "opensearch", "service"),
            pill("pgvector", rag_active == "pgvector", "Postgres"),
        ]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{config.app.name} — Architecture</title>
<style>
  :root {{
    --bg: #0b1020;
    --bg-2: #0f1530;
    --panel: rgba(255,255,255,0.04);
    --panel-2: rgba(255,255,255,0.06);
    --border: rgba(255,255,255,0.08);
    --border-2: rgba(255,255,255,0.14);
    --text: #e6eaf2;
    --muted: #9aa3b8;
    --accent: {config.app.theme};
    --accent-2: #8b5cf6;
    --good: #10b981;
    --warn: #f59e0b;
    --shadow: 0 10px 40px rgba(0,0,0,0.35);
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Inter, Roboto, "Helvetica Neue", Arial;
    background:
      radial-gradient(1200px 600px at 10% -10%, rgba(59,130,246,0.18), transparent 60%),
      radial-gradient(900px 500px at 110% 10%, rgba(139,92,246,0.18), transparent 55%),
      linear-gradient(180deg, var(--bg), var(--bg-2));
    color: var(--text);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 56px 28px 96px; }}

  /* Header */
  .hero {{ display: flex; align-items: center; gap: 18px; margin-bottom: 8px; }}
  .logo {{
    width: 48px; height: 48px; border-radius: 14px;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    box-shadow: 0 6px 24px rgba(59,130,246,0.35);
    display: grid; place-items: center; color: white; font-weight: 800; font-size: 22px;
  }}
  h1 {{ margin: 0; font-size: 30px; letter-spacing: -0.02em; }}
  .sub-hero {{ color: var(--muted); margin: 6px 0 32px; font-size: 14px; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 36px; }}
  .chip {{
    font-size: 12px; color: var(--muted); border: 1px solid var(--border);
    padding: 6px 10px; border-radius: 999px; background: var(--panel);
  }}
  .chip b {{ color: var(--text); font-weight: 600; }}
  .chip.on b {{ color: var(--good); }}
  .chip.off b {{ color: var(--warn); }}

  /* Section titles */
  .section-title {{
    display: flex; align-items: baseline; gap: 10px;
    margin: 28px 0 14px; font-size: 13px; letter-spacing: 0.16em;
    text-transform: uppercase; color: var(--muted);
  }}
  .section-title::before {{
    content: ""; width: 8px; height: 8px; border-radius: 999px;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    box-shadow: 0 0 12px var(--accent);
  }}

  /* Stack diagram (top-to-bottom flow) */
  .stack {{ display: grid; gap: 14px; }}
  .layer {{
    border: 1px solid var(--border); background: var(--panel);
    border-radius: 18px; padding: 18px 20px; position: relative;
    backdrop-filter: blur(6px);
  }}
  .layer h3 {{ margin: 0 0 4px; font-size: 16px; }}
  .layer .meta {{ color: var(--muted); font-size: 12.5px; }}
  .layer .body {{ margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }}
  .tag {{
    font-size: 12px; padding: 5px 10px; border-radius: 8px;
    background: var(--panel-2); border: 1px solid var(--border);
    color: var(--text);
  }}
  .arrow {{
    height: 24px; display: grid; place-items: center; color: var(--muted);
  }}
  .arrow::before {{
    content: ""; width: 2px; height: 100%;
    background: linear-gradient(180deg, transparent, rgba(255,255,255,0.18), transparent);
  }}

  /* Two-column inside backend */
  .grid-2 {{ display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; margin-top: 12px; }}
  @media (max-width: 720px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
  .mini {{
    border: 1px solid var(--border); background: var(--panel-2);
    border-radius: 12px; padding: 12px 14px;
  }}
  .mini h4 {{ margin: 0 0 6px; font-size: 13px; }}
  .mini p {{ margin: 0; font-size: 12.5px; color: var(--muted); }}

  /* Pluggable cards */
  .cards {{
    display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 14px;
  }}
  @media (max-width: 820px) {{ .cards {{ grid-template-columns: 1fr; }} }}
  .card {{
    border: 1px solid var(--border); background: var(--panel);
    border-radius: 18px; padding: 18px 20px;
    box-shadow: var(--shadow);
  }}
  .card .head {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom: 4px; }}
  .card h3 {{ margin: 0; font-size: 15px; letter-spacing: 0.02em; }}
  .card .selector {{ font-size: 11.5px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .card .factory {{ font-size: 11.5px; color: var(--muted); margin-bottom: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .pills {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .pill {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 7px 11px; border-radius: 999px;
    background: var(--panel-2); border: 1px solid var(--border);
    font-size: 12.5px; color: var(--text);
  }}
  .pill .dot {{
    width: 8px; height: 8px; border-radius: 999px;
    background: rgba(255,255,255,0.25);
  }}
  .pill .sub {{ color: var(--muted); font-size: 11.5px; }}
  .pill.active {{
    border-color: transparent;
    background: linear-gradient(135deg, rgba(59,130,246,0.22), rgba(139,92,246,0.22));
    box-shadow: inset 0 0 0 1px var(--border-2), 0 0 0 1px rgba(59,130,246,0.4);
  }}
  .pill.active .dot {{
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    box-shadow: 0 0 10px var(--accent);
  }}

  /* Deployment & flows */
  .deploy {{
    display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px;
  }}
  @media (max-width: 820px) {{ .deploy {{ grid-template-columns: 1fr; }} }}
  .svc {{
    border: 1px solid var(--border); background: var(--panel);
    border-radius: 14px; padding: 14px 16px;
  }}
  .svc h4 {{ margin: 0 0 4px; font-size: 13.5px; }}
  .svc code {{ font-size: 11.5px; color: var(--muted); }}

  .flow {{
    border: 1px solid var(--border); background: var(--panel);
    border-radius: 18px; padding: 18px 20px;
  }}
  .flow + .flow {{ margin-top: 12px; }}
  .flow h4 {{ margin: 0 0 6px; font-size: 13px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); }}
  .flow p {{ margin: 0; font-size: 14px; line-height: 1.55; color: var(--text); }}
  .kbd {{
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px;
    background: rgba(255,255,255,0.06); border: 1px solid var(--border);
    padding: 2px 6px; border-radius: 6px;
  }}

  footer {{ margin-top: 36px; color: var(--muted); font-size: 12px; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <div class="logo">J</div>
    <div>
      <h1>{config.app.name} — Architecture</h1>
      <div class="sub-hero">Layered system with pluggable vendors at every seam.</div>
    </div>
  </div>

  <div class="chips">
    <span class="chip">LLM <b>{llm_active}</b></span>
    <span class="chip">STT <b>{stt_active}</b></span>
    <span class="chip">TTS <b>{tts_active}</b></span>
    <span class="chip">RAG <b>{rag_active}</b></span>
    <span class="chip {'on' if config.voice.enabled else 'off'}">Voice <b>{voice_on}</b></span>
    <span class="chip {'on' if config.rag.enabled else 'off'}">RAG <b>{rag_on}</b></span>
    <span class="chip {'on' if config.auth.enabled else 'off'}">Auth <b>{auth_on}</b></span>
  </div>

  <div class="section-title">Request stack</div>
  <div class="stack">

    <div class="layer">
      <h3>Clients</h3>
      <div class="meta">React 18 SPA · embeddable widget · WebRTC for voice</div>
      <div class="body">
        <span class="tag">React 18</span>
        <span class="tag">Vite 5</span>
        <span class="tag">Zustand</span>
        <span class="tag">React Router 6</span>
        <span class="tag">TailwindCSS</span>
        <span class="tag">axios</span>
        <span class="tag">react-markdown</span>
        <span class="tag">lucide-react</span>
        <span class="tag">widget.js drop-in</span>
      </div>
    </div>

    <div class="arrow"></div>

    <div class="layer">
      <h3>Edge — nginx</h3>
      <div class="meta">Reverse proxy in the <span class="kbd">frontend</span> container → upstream <span class="kbd">backend:8000</span></div>
      <div class="body">
        <span class="tag">/api</span>
        <span class="tag">/ws</span>
        <span class="tag">/webrtc</span>
        <span class="tag">UDP 7880-7889</span>
      </div>
    </div>

    <div class="arrow"></div>

    <div class="layer">
      <h3>Backend — FastAPI · Uvicorn</h3>
      <div class="meta">REST + WebSocket + WebRTC, all on one app · loguru</div>
      <div class="grid-2">
        <div class="mini">
          <h4>REST <span class="kbd">api/*</span></h4>
          <p>auth · conversations · admin · voice/bind · architecture</p>
        </div>
        <div class="mini">
          <h4>WebSocket <span class="kbd">ws/chat.py</span></h4>
          <p>Streaming text chat over <span class="kbd">/ws/chat/{{id}}</span></p>
        </div>
        <div class="mini">
          <h4>WebRTC <span class="kbd">voice/stream.py</span></h4>
          <p>fastrtc <span class="kbd">Stream</span> + <span class="kbd">ReplyOnPause</span> mounted on FastAPI</p>
        </div>
        <div class="mini">
          <h4>Agent <span class="kbd">llm/agent.py</span></h4>
          <p>LangGraph <span class="kbd">create_react_agent</span> · MemorySaver per <span class="kbd">thread_id</span></p>
        </div>
        <div class="mini">
          <h4>Tools</h4>
          <p>{enabled_tools}</p>
        </div>
        <div class="mini">
          <h4>Repositories</h4>
          <p>SQLAlchemy + Alembic · <span class="kbd">conversations</span>, <span class="kbd">messages</span></p>
        </div>
      </div>
    </div>

  </div>

  <div class="section-title">Pluggable layers — vendor options</div>
  <div class="cards">

    <div class="card">
      <div class="head"><h3>LLM provider</h3><span class="selector">config.llm.provider</span></div>
      <div class="factory">backend/app/llm/factory.py</div>
      <div class="pills">{llm_pills}</div>
    </div>

    <div class="card">
      <div class="head"><h3>Speech-to-Text</h3><span class="selector">config.voice.stt_model</span></div>
      <div class="factory">backend/app/voice/stt.py</div>
      <div class="pills">{stt_pills}</div>
    </div>

    <div class="card">
      <div class="head"><h3>Text-to-Speech</h3><span class="selector">config.voice.tts_model</span></div>
      <div class="factory">backend/app/voice/tts.py</div>
      <div class="pills">{tts_pills}</div>
    </div>

    <div class="card">
      <div class="head"><h3>RAG vector store</h3><span class="selector">config.rag.store</span></div>
      <div class="factory">embeddings: {config.rag.embedding_model}</div>
      <div class="pills">{rag_pills}</div>
    </div>

    <div class="card">
      <div class="head"><h3>Database</h3><span class="selector">config.database.url</span></div>
      <div class="factory">SQLAlchemy · Alembic migrations</div>
      <div class="pills">
        <div class="pill active"><span class="dot"></span><span class="lbl">{db_active}</span></div>
        <div class="pill"><span class="dot"></span><span class="lbl">Postgres / MySQL</span><span class="sub">any SQLAlchemy URL</span></div>
      </div>
    </div>

    <div class="card">
      <div class="head"><h3>Web search · Auth · Logging</h3><span class="selector">cross-cutting</span></div>
      <div class="factory">tools, security, observability</div>
      <div class="pills">
        <div class="pill"><span class="dot"></span><span class="lbl">DDGS</span><span class="sub">DuckDuckGo</span></div>
        <div class="pill"><span class="dot"></span><span class="lbl">PyJWT</span><span class="sub">auth</span></div>
        <div class="pill"><span class="dot"></span><span class="lbl">loguru</span><span class="sub">logs</span></div>
        <div class="pill"><span class="dot"></span><span class="lbl">aiortc</span><span class="sub">via fastrtc</span></div>
      </div>
    </div>

  </div>

  <div class="section-title">Deployment — docker-compose</div>
  <div class="deploy">
    <div class="svc"><h4>backend</h4><code>./backend (FastAPI)</code></div>
    <div class="svc"><h4>frontend</h4><code>./frontend (nginx + SPA + widget)</code></div>
    <div class="svc"><h4>ollama <span class="kbd">profile</span></h4><code>ollama/ollama:latest</code></div>
    <div class="svc"><h4>chromadb <span class="kbd">profile</span></h4><code>chromadb/chroma:latest</code></div>
    <div class="svc"><h4>opensearch <span class="kbd">profile</span></h4><code>opensearchproject/opensearch:2</code></div>
    <div class="svc"><h4>postgres <span class="kbd">profile</span></h4><code>pgvector/pgvector:pg16</code></div>
  </div>

  <div class="section-title">End-to-end flows</div>

  <div class="flow">
    <h4>Text chat</h4>
    <p>Browser → <span class="kbd">WSS /ws/chat/{{id}}</span> → <span class="kbd">ws/chat.py</span> → LangGraph agent (+ tools) → stream chunks back → SQLite write on <span class="kbd">done</span>.</p>
  </div>
  <div class="flow">
    <h4>Voice</h4>
    <p>Browser mic → WebRTC offer → fastrtc <span class="kbd">Stream</span> + <span class="kbd">ReplyOnPause</span> → STT → agent → sentence-buffered TTS → SRTP back to speaker.</p>
  </div>
  <div class="flow">
    <h4>Voice bind</h4>
    <p><span class="kbd">POST /api/voice/bind</span> injects <span class="kbd">conversation_id</span> into the per-<span class="kbd">webrtc_id</span> handler so subsequent turns route to the right conversation.</p>
  </div>

  <footer>Generated live from <span class="kbd">/api/architecture</span> · {config.app.name} v0.1.0</footer>
</div>
</body>
</html>"""


@router.get("/api/architecture", response_class=HTMLResponse)
def architecture():
    """Render the project's architecture as a self-contained HTML page.
    Active vendor at each pluggable seam reflects the current config."""
    return HTMLResponse(_render(get_config()))
