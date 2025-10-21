"""Agent API Server - OpenAI-compatible API for Luna agents.

Fully featured OpenAI-compatible server exposed locally on port 8080.
Discovers agents from core/agents/*/ directories.
"""
import os
import sys
import time
import uuid
import json
import glob
import inspect
import importlib.util
from types import ModuleType
from typing import List, Optional, Literal, Dict, Any, Tuple, AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, Response, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---- Config ----
DEBUG = os.getenv("AGENT_API_DEBUG", "true").lower() in ("1", "true", "yes", "on")
DEFAULT_AGENT = os.getenv("DEFAULT_AGENT", "simple_agent")

# Discovery: scan core/agents/*/ for agent.py files
AGENTS_ROOT = PROJECT_ROOT / "core" / "agents"

app = FastAPI(title="Luna Agent API (OpenAI-compatible, No Auth)")

# Add CORS for localhost and network access - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for network access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Request/Response models ----
class ChatMessage(BaseModel):
    """Chat message in OpenAI format."""
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """Chat completion request in OpenAI format."""
    model: Optional[str] = Field(default=None)
    messages: List[ChatMessage]
    stream: Optional[bool] = Field(default=False)
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    n: Optional[int] = Field(default=1)


# ---- Agent Registry ----
AGENTS: Dict[str, ModuleType] = {}
AGENT_PATHS: Dict[str, str] = {}


def _split_history_and_prompt(messages: List[ChatMessage]) -> Tuple[str, str]:
    """Split messages into chat history and final user prompt."""
    user_indexes = [i for i, m in enumerate(messages) if m.role == "user" and (m.content or "").strip()]
    if not user_indexes:
        raise HTTPException(status_code=400, detail="no user message provided")
    
    last_user_idx = user_indexes[-1]
    last_user_text = (messages[last_user_idx].content or "").strip()

    prior = messages[:last_user_idx]
    if not prior:
        return "", last_user_text

    lines: List[str] = []
    for m in prior:
        c = (m.content or "").strip()
        if not c:
            continue
        if m.role == "user":
            lines.append(f"user: {c}")
        elif m.role == "assistant":
            lines.append(f"assistant: {c}")
        # Ignore system/tool/function in chat_history
    
    return "\n".join(lines), last_user_text


def _extract_memory(messages: List[ChatMessage], header_memory: Optional[str]) -> Optional[str]:
    """Extract memory from X-Luna-Memory header."""
    # Only honor X-Luna-Memory header (ignore system messages for memory)
    if header_memory and header_memory.strip():
        return header_memory.strip()
    return None


def _make_chat_completion_payload(model: str, content: str) -> Dict[str, Any]:
    """Create OpenAI-compatible chat completion response."""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


async def _sse_gen(final_text: str, model_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE stream for a final text response."""
    cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    
    chunk1 = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model_id,
        "choices": [
            {"index": 0, "delta": {"role": "assistant", "content": final_text}, "finish_reason": None}
        ],
    }
    yield f"data: {json.dumps(chunk1)}\n\n"
    
    chunk2 = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model_id,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(chunk2)}\n\n"
    yield "data: [DONE]\n\n"


async def _sse_token_stream(
    mod: ModuleType,
    user_prompt: str,
    chat_history: Optional[str],
    memory: Optional[str],
    model_id: str
) -> AsyncGenerator[str, None]:
    """Stream token-by-token SSE compatible with OpenAI Chat Completions."""
    cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    # Send initial role chunk
    first = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model_id,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(first)}\n\n"

    yielded_any = False
    try:
        agen = getattr(mod, "run_agent_stream", None)
        if agen is None:
            raise RuntimeError("run_agent_stream not available")
        
        async for token in agen(user_prompt, chat_history=chat_history or None, memory=memory):
            if not isinstance(token, str) or token == "":
                continue
            yielded_any = True
            chunk = {
                "id": cid,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_id,
                "choices": [
                    {"index": 0, "delta": {"content": token}, "finish_reason": None}
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
    except Exception:
        yielded_any = False if not yielded_any else yielded_any

    # Close out the stream
    if not yielded_any:
        empty = {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model_id,
            "choices": [{"index": 0, "delta": {"content": ""}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(empty)}\n\n"

    end = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model_id,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(end)}\n\n"
    yield "data: [DONE]\n\n"


def _is_async_run_agent(mod: ModuleType) -> bool:
    """Check if module has async run_agent function."""
    fn = getattr(mod, "run_agent", None)
    return inspect.iscoroutinefunction(fn)


def _import_module_from_path(path: str) -> Optional[ModuleType]:
    """Import a Python module from a file path."""
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod
    except Exception:
        return None


def _discover_agents() -> Dict[str, ModuleType]:
    """Discover agents from core/agents/*/agent.py."""
    found: Dict[str, ModuleType] = {}
    
    print(f"[Agent API] Discovering agents from: {AGENTS_ROOT}", flush=True)
    
    if not AGENTS_ROOT.exists():
        print(f"[Agent API] ERROR: Agents root directory does not exist: {AGENTS_ROOT}", flush=True)
        return found
    
    # Scan for agent.py files in subdirectories
    for agent_dir in AGENTS_ROOT.iterdir():
        if not agent_dir.is_dir():
            print(f"[Agent API] Skipping non-directory: {agent_dir.name}", flush=True)
            continue
        
        agent_file = agent_dir / "agent.py"
        if not agent_file.exists():
            print(f"[Agent API] Skipping {agent_dir.name}: no agent.py found", flush=True)
            continue
        
        print(f"[Agent API] Found agent file: {agent_file}", flush=True)
        
        # Import the module
        mod = _import_module_from_path(str(agent_file))
        if not mod:
            print(f"[Agent API] ERROR: Failed to import {agent_file}", flush=True)
            continue
        
        print(f"[Agent API] Successfully imported {agent_dir.name}", flush=True)
        
        # Verify it has async run_agent
        if not _is_async_run_agent(mod):
            print(f"[Agent API] Skipping {agent_dir.name}: no async run_agent function", flush=True)
            continue
        
        # Register with agent directory name as model ID
        model_id = agent_dir.name
        found[model_id] = mod
        AGENT_PATHS[model_id] = str(agent_file.relative_to(PROJECT_ROOT))
        print(f"[Agent API] ✓ Registered agent: {model_id}", flush=True)
    
    return found


def _maybe_print_startup_models() -> None:
    """Print discovered agents at startup."""
    try:
        print("[Agent API] ========================================", flush=True)
        print(f"[Agent API] Discovered {len(AGENTS)} agent(s):", flush=True)
        for k, mod in AGENTS.items():
            line = f"[Agent API]   - {k}"
            p = AGENT_PATHS.get(k)
            if p:
                line += f" | path={p}"
            print(line, flush=True)
        print("[Agent API] ========================================", flush=True)
    except Exception as e:
        print(f"[Agent API] ERROR printing agents: {e}", flush=True)


def _init_agents() -> None:
    """Initialize agent registry."""
    global AGENTS
    print("[Agent API] Initializing agent registry...", flush=True)
    AGENTS = _discover_agents()
    print(f"[Agent API] Agent discovery complete. Found {len(AGENTS)} agents.", flush=True)
    
    # Warm agents if they expose initialize_runtime()
    for k, mod in AGENTS.items():
        init = getattr(mod, "initialize_runtime", None)
        if callable(init):
            try:
                print(f"[Agent API] Initializing runtime for {k}...", flush=True)
                init()
            except Exception as e:
                # Warming is best-effort
                print(f"[Agent API] WARNING: Failed to initialize {k}: {e}", flush=True)


# ---- Lifecycle ----
@app.on_event("startup")
async def _on_startup() -> None:
    """Initialize agents on startup."""
    print("[Agent API] Agent API starting up...", flush=True)
    _init_agents()
    _maybe_print_startup_models()
    # NOTE: Service manager is used for discovery/status only.
    # The Supervisor is responsible for actually starting extension services.
    # DO NOT call init_and_start() here - it would create duplicate services!
    print("[Agent API] Agent API startup complete, ready for requests", flush=True)


# ---- Routes ----
@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/extensions")
async def list_extensions_status() -> Dict[str, Any]:
    """List discovered extensions with UI and services status."""
    try:
        # Query supervisor API for extension status (supervisor manages all services)
        import httpx
        try:
            supervisor_host = os.getenv('SUPERVISOR_HOST', '127.0.0.1')
            response = httpx.get(f"http://{supervisor_host}:9999/extensions", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                extensions = data.get('extensions', [])
                enabled_count = sum(1 for e in extensions if e.get('enabled', True))
                disabled_count = len(extensions) - enabled_count
                print(f"[AgentAPI] GET /extensions - Returning {len(extensions)} extensions ({enabled_count} enabled, {disabled_count} disabled): {[e['name'] for e in extensions]}", flush=True)
                return {"extensions": extensions}
        except Exception as e:
            print(f"[AgentAPI] GET /extensions - Failed to query supervisor: {e}", flush=True)
        
        # Fallback to service_manager if supervisor is not available
        from core.utils.service_manager import get_manager
        mgr = get_manager()
        extensions = mgr.list_extensions()
        enabled_count = sum(1 for e in extensions if e.get('enabled', True))
        disabled_count = len(extensions) - enabled_count
        print(f"[AgentAPI] GET /extensions - Returning {len(extensions)} extensions (fallback): {[e['name'] for e in extensions]}", flush=True)
        return {"extensions": extensions}
    except Exception as e:
        print(f"[AgentAPI] GET /extensions - Error: {e}", flush=True)
        return {"extensions": []}


@app.get("/extensions/{name}")
async def get_extension_status(name: str) -> Dict[str, Any]:
    try:
        from core.utils.service_manager import get_manager
        mgr = get_manager()
        data = mgr.get_extension(name)
        if not data:
            raise HTTPException(status_code=404, detail="extension not found")
        return data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="internal error")


@app.post("/extensions/{name}/ui/restart")
async def restart_extension_ui(name: str) -> Dict[str, Any]:
    try:
        from core.utils.service_manager import get_manager
        mgr = get_manager()
        ok = mgr.restart_ui(name)
        if not ok:
            raise HTTPException(status_code=404, detail="ui not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="internal error")


@app.post("/extensions/{name}/services/{service}/restart")
async def restart_extension_service(name: str, service: str) -> Dict[str, Any]:
    try:
        from core.utils.service_manager import get_manager
        mgr = get_manager()
        ok = mgr.restart_service(name, service)
        if not ok:
            raise HTTPException(status_code=404, detail="service not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="internal error")


@app.get("/v1/models")
async def list_models():
    """List available models (agents)."""
    now = int(time.time())
    data = [
        {"id": mid, "object": "model", "created": now, "owned_by": "luna"}
        for mid in sorted(AGENTS.keys())
    ]
    return {"object": "list", "data": data}


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
    """Get details of a specific model (agent)."""
    if model_id not in AGENTS:
        raise HTTPException(status_code=404, detail="model not found")
    return {"id": model_id, "object": "model", "created": int(time.time()), "owned_by": "luna"}


@app.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    response: Response,
    memory_header: Optional[str] = Header(default=None, alias="X-Luna-Memory"),
):
    """Chat completion endpoint (OpenAI-compatible)."""
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    model_id = (body.model or "").strip() or DEFAULT_AGENT
    mod = AGENTS.get(model_id)
    
    if not mod:
        # Refresh once in case of hot add
        _init_agents()
        mod = AGENTS.get(model_id)
        if not mod:
            raise HTTPException(status_code=404, detail=f"unknown model '{model_id}'")

    chat_history, user_prompt = _split_history_and_prompt(body.messages)
    memory = _extract_memory(body.messages, memory_header)

    # Streaming path
    if body.stream:
        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
        try:
            # Prefer token streaming if available
            if hasattr(mod, "run_agent_stream"):
                return StreamingResponse(
                    _sse_token_stream(mod, user_prompt, chat_history or None, memory, model_id),
                    media_type="text/event-stream",
                    headers=headers,
                )
        except Exception:
            pass

        # Fallback: compute final text and stream in one chunk
        try:
            result_fallback = await mod.run_agent(  # type: ignore[attr-defined]
                user_prompt,
                chat_history=chat_history or None,
                memory=memory
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"agent error: {exc}") from exc
        
        final_text_fallback: str = str(getattr(result_fallback, "final", result_fallback))
        return StreamingResponse(
            _sse_gen(final_text_fallback, model_id),
            media_type="text/event-stream",
            headers=headers
        )

    # Non-streaming path
    try:
        t0 = time.perf_counter()
        result = await mod.run_agent(  # type: ignore[attr-defined]
            user_prompt,
            chat_history=chat_history or None,
            memory=memory
        )
        elapsed = round(time.perf_counter() - t0, 3)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"agent error: {exc}") from exc

    final_text: str = str(getattr(result, "final", result))

    # Add timings header
    timings_list = []
    try:
        for tm in getattr(result, "timings", []) or []:
            timings_list.append({
                "name": getattr(tm, "name", "unknown"),
                "seconds": getattr(tm, "seconds", None)
            })
    except Exception:
        pass
    
    timing_header = {
        "steps": timings_list,
        "server_elapsed_s": elapsed,
        "agent": model_id
    }
    response.headers["X-Luna-Timings"] = json.dumps(timing_header)

    payload = _make_chat_completion_payload(model_id, final_text)
    return JSONResponse(content=payload)


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("AGENT_API_HOST", "0.0.0.0")
    port = int(os.environ.get("AGENT_API_PORT", "8080"))
    uvicorn.run(app, host=host, port=port, reload=False)

