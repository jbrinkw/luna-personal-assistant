from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
import re
import uuid
from typing import Any, Dict, List

# External HTTP client for Langflow proxy
try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - runtime import; ensure dependency installed in env
    httpx = None  # delayed import check in handler

# Load env from repo root and local via python-dotenv
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Best-effort repo root detection: .../core/hub/ui_hub -> repo root is three parents up
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app = FastAPI(title="Agent Hub")

static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def parse_agents_from_env() -> list[dict]:
    # Format: AGENT_LINKS="ChefByte:http://localhost:8030,CoachByte:http://localhost:8031"
    raw = os.environ.get("AGENT_LINKS")
    agents: list[dict] = []
    if raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for p in parts:
            if ":" in p:
                name, url = p.split(":", 1)
                slug = slugify(name)
                agents.append({"name": name.strip(), "slug": slug, "url": url.strip()})
    if not agents:
        # defaults
        agents = [
            {"name": "ChefByte", "slug": "chefbyte", "url": "http://localhost:8030"},
            {"name": "CoachByte", "slug": "coachbyte", "url": "http://localhost:8031"},
        ]
    return agents


def slugify(name: str) -> str:
    return "".join(ch.lower() for ch in name if ch.isalnum())


def get_agents():
    # Recompute each request so env changes are picked up in dev
    return parse_agents_from_env()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    agents = get_agents()
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "agents": agents, "current_slug": None},
    )


@app.get("/app/{slug}", response_class=HTMLResponse)
def app_view(slug: str, request: Request):
    agents = get_agents()
    agent = next((a for a in agents if a["slug"] == slug), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return templates.TemplateResponse(
        "app.html",
        {
            "request": request,
            "agents": agents,
            "current_slug": slug,
            "agent": agent,
        },
    )


@app.get("/health")
def health():
    return JSONResponse({"ok": True})


# =============================
# Langflow Chat Proxy (CLI parity)
# =============================

# Mirror CLI envs and defaults
if load_dotenv:
    # Load .env from repo root first, then from this directory
    load_dotenv(os.path.join(REPO_ROOT, ".env"))
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    load_dotenv()
LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://localhost:7860").rstrip("/")
LANGFLOW_FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "").strip()
LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY")
LANGFLOW_INPUT_TYPE = os.getenv("LANGFLOW_INPUT_TYPE", "chat")
LANGFLOW_OUTPUT_TYPE = os.getenv("LANGFLOW_OUTPUT_TYPE", "chat")
LANGFLOW_TIMEOUT = float(os.getenv("LANGFLOW_TIMEOUT", "120"))
LANGFLOW_TWEAKS_FILE = os.getenv("LANGFLOW_TWEAKS_FILE")


def _load_tweaks_from_file(path: str | None):
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


_TWEAKS_DEFAULT = _load_tweaks_from_file(LANGFLOW_TWEAKS_FILE)


def _extract_langflow_from_test_proxy() -> tuple[str | None, str | None]:
    """Attempt to read base_url and flow_id from core/tools/test_proxy.py's url variable.

    Returns (base_url, flow_id) or (None, None) if not found.
    """
    candidate = os.path.join(REPO_ROOT, "core", "tools", "test_proxy.py")
    try:
        with open(candidate, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None, None

    m = re.search(r"url\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not m:
        return None, None
    full_url = m.group(1)
    split_marker = "/api/v1/run/"
    if split_marker not in full_url:
        return None, None
    base, after = full_url.split(split_marker, 1)
    flow_id = after.split("?")[0].split("/")[0]
    base_url = base.rstrip("/")
    return base_url, flow_id


# Fallback: if FLOW_ID not provided, try reading from core/tools/test_proxy.py
if not LANGFLOW_FLOW_ID:
    _base_url, _flow_id = _extract_langflow_from_test_proxy()
    if _flow_id:
        LANGFLOW_FLOW_ID = _flow_id
    # Only override base URL if explicitly provided by test proxy and the current value is the default
    if _base_url and (LANGFLOW_URL == "http://localhost:7860" or not LANGFLOW_URL):
        LANGFLOW_URL = _base_url


def _build_headers(api_key: str | None) -> dict:
    headers: dict = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-Langflow-Api-Key"] = api_key
    return headers


def _build_payload(
    message: str,
    input_type: str,
    output_type: str,
    session_id: str | None,
    tweaks: dict | None,
) -> dict:
    payload: dict = {
        "input_value": message,
        "input_type": input_type,
        "output_type": output_type,
    }
    if session_id:
        payload["session_id"] = session_id
    if tweaks:
        payload["tweaks"] = tweaks
    return payload


def _try_extract_text(response_json: object) -> str | None:
    # Heuristics similar to CLI try_extract_text
    if response_json is None or not isinstance(response_json, dict):
        return None

    for key in ("text", "message", "output_text", "content", "result"):
        val = response_json.get(key)  # type: ignore[attr-defined]
        if isinstance(val, str) and val.strip():
            return val

    try:
        outputs = response_json.get("outputs")  # type: ignore[attr-defined]
        if isinstance(outputs, list) and outputs:
            first = outputs[0]
            inner_outputs = first.get("outputs") if isinstance(first, dict) else None
            if isinstance(inner_outputs, list) and inner_outputs:
                first_inner = inner_outputs[0]
                results = first_inner.get("results") if isinstance(first_inner, dict) else None
                if isinstance(results, dict):
                    for key in ("text", "message", "output_text", "content"):
                        val = results.get(key)
                        if isinstance(val, str) and val.strip():
                            return val
                        if isinstance(val, dict):
                            inner_text = val.get("text")
                            if isinstance(inner_text, str) and inner_text.strip():
                                return inner_text
                artifacts = first_inner.get("artifacts") if isinstance(first_inner, dict) else None
                if isinstance(artifacts, dict):
                    for _, v in artifacts.items():
                        if isinstance(v, str) and v.strip():
                            return v
    except Exception:
        pass

    try:
        return json.dumps(response_json, ensure_ascii=False)
    except Exception:
        return str(response_json)


@app.post("/api/langflow/chat")
async def langflow_chat(request: Request):
    # Compatibility alias: route all old Langflow chat requests to the agent API
    return await agent_chat(request)


# =============================
# Agent (OpenAI-compatible) Chat Proxy
# =============================

# Configure target for the new agent API
AGENT_API_HOST = os.getenv("AGENT_API_HOST", "127.0.0.1").strip()
AGENT_API_PORT = int(os.getenv("AGENT_API_PORT", "8010"))
AGENT_API_TIMEOUT = float(os.getenv("AGENT_API_TIMEOUT", "60"))
AGENT_SESSION_COOKIE = os.getenv("AGENT_SESSION_COOKIE", "agent_sid")
AGENT_MAX_HISTORY = int(os.getenv("AGENT_MAX_HISTORY", "25"))

# In-memory per-session message history for the hub chat drawer
_SESSION_MESSAGES: Dict[str, List[Dict[str, Any]]] = {}

def _get_or_create_session_id(request: Request) -> tuple[str, bool]:
    sid = request.cookies.get(AGENT_SESSION_COOKIE)
    if sid and isinstance(sid, str) and sid.strip():
        return sid, False
    return uuid.uuid4().hex, True


@app.post("/api/agent/chat")
async def agent_chat(request: Request):
    if httpx is None:
        return JSONResponse({"error": "httpx not installed on server"}, status_code=500)

    try:
        body = await request.json()
    except Exception:
        body = {}

    # Accept either a simple 'message' string or full OpenAI-style 'messages' array
    msg = (body or {}).get("message")
    messages = (body or {}).get("messages")
    # Establish or retrieve session and merge server-side memory
    sid, is_new = _get_or_create_session_id(request)
    stored = _SESSION_MESSAGES.get(sid, [])

    if messages and isinstance(messages, list):
        # If client provided full history, trust it and overwrite stored copy
        merged = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
        _SESSION_MESSAGES[sid] = merged[-AGENT_MAX_HISTORY:]
        out_messages = _SESSION_MESSAGES[sid]
    else:
        if not msg or not isinstance(msg, str):
            return JSONResponse({"error": "message or messages is required"}, status_code=400)
        # Append new user message to stored history
        stored.append({"role": "user", "content": msg})
        _SESSION_MESSAGES[sid] = stored[-AGENT_MAX_HISTORY:]
        out_messages = _SESSION_MESSAGES[sid]

    url = f"http://{AGENT_API_HOST}:{AGENT_API_PORT}/v1/chat/completions"

    async with httpx.AsyncClient(timeout=AGENT_API_TIMEOUT) as client:
        try:
            r = await client.post(url, json={"messages": out_messages})
        except httpx.TimeoutException:
            return JSONResponse({"error": "timeout"}, status_code=504)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=502)

    if r.status_code != 200:
        return JSONResponse({"error": "Agent error", "detail": r.text}, status_code=r.status_code)

    # Agent returns plain text body; append assistant reply to session history
    reply_text = (r.text or "").strip()
    _SESSION_MESSAGES.setdefault(sid, [])
    _SESSION_MESSAGES[sid].append({"role": "assistant", "content": reply_text})
    _SESSION_MESSAGES[sid] = _SESSION_MESSAGES[sid][-AGENT_MAX_HISTORY:]

    resp = JSONResponse({"response": reply_text})
    if is_new:
        resp.set_cookie(AGENT_SESSION_COOKIE, sid, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    return resp


@app.delete("/api/agent/session")
def agent_session_reset(request: Request):
    sid = request.cookies.get(AGENT_SESSION_COOKIE)
    if sid in _SESSION_MESSAGES:
        try:
            del _SESSION_MESSAGES[sid]
        except Exception:
            pass
    resp = JSONResponse({"ok": True})
    try:
        resp.delete_cookie(AGENT_SESSION_COOKIE)
    except Exception:
        pass
    return resp


@app.delete("/api/langflow/session")
def langflow_session_reset():
    # Compatibility alias: clear agent session (stateless) and remove legacy cookie if present
    resp = agent_session_reset()
    try:
        resp.delete_cookie("lf_session_id")
    except Exception:
        pass
    return resp


