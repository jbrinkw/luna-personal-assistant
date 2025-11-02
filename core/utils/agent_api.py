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
import secrets
import importlib.util
from types import ModuleType
from typing import List, Optional, Literal, Dict, Any, Tuple, AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, Response, HTTPException, Request, Header, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.utils.caddy_control import reload_caddy

# Optional .env
try:
    from dotenv import load_dotenv, set_key, find_dotenv
    load_dotenv()
except Exception:
    print("Warning: python-dotenv not fully available")
    set_key = None
    find_dotenv = None

# ---- Auth Setup ----
def get_or_generate_api_key() -> str:
    """Get API key from environment or generate and save a new one"""
    api_key = os.getenv("AGENT_API_KEY")
    
    if api_key:
        print(f"[Agent API] Using existing AGENT_API_KEY from environment")
        return api_key
    
    # Generate new API key
    api_key = f"sk-luna-{secrets.token_urlsafe(32)}"
    print(f"[Agent API] No AGENT_API_KEY found, generated new key: {api_key}")
    
    # Try to save to .env file
    if set_key and find_dotenv:
        try:
            env_file = find_dotenv()
            if not env_file:
                # Create .env file if it doesn't exist
                env_file = PROJECT_ROOT / ".env"
                env_file.touch()
                env_file = str(env_file)
            
            set_key(env_file, "AGENT_API_KEY", api_key, quote_mode="never")
            print(f"[Agent API] Saved AGENT_API_KEY to {env_file}")
        except Exception as e:
            print(f"[Agent API] Warning: Could not save API key to .env file: {e}")
            print(f"[Agent API] Please manually add to .env: AGENT_API_KEY={api_key}")
    else:
        print(f"[Agent API] Please manually add to .env: AGENT_API_KEY={api_key}")
    
    return api_key

# Initialize API key
API_KEY = get_or_generate_api_key()

# Get public URL from environment
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8080")

# Security scheme
security = HTTPBearer()

# ---- Config ----
DEBUG = os.getenv("AGENT_API_DEBUG", "true").lower() in ("1", "true", "yes", "on")
DEFAULT_AGENT = os.getenv("DEFAULT_AGENT", "simple_agent")
_UNPROTECTED_PATHS = {"/", "/healthz"}

# Discovery: scan core/agents/*/ for agent.py files
AGENTS_ROOT = PROJECT_ROOT / "core" / "agents"

app = FastAPI(title="Luna Agent API", description="OpenAI-compatible API for Luna agents")

# Add CORS for localhost and network access - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for network access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key validation
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the API key from the Authorization header"""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

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

# ---- Preset Caches ----
_TOOL_CACHE: Dict[str, Any] = {}  # All tools cached at startup
_PRESET_TOOL_CACHE: Dict[str, set] = {}  # Filtered tool names per preset
_PRESET_METADATA: Dict[str, Dict[str, Any]] = {}  # Preset metadata for /v1/models


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


def _trigger_caddy_reload(reason: str) -> None:
    try:
        reload_caddy(PROJECT_ROOT, reason=f"agent-api:{reason}", quiet=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[AgentAPI] Warning: Failed to reload Caddy ({reason}): {exc}", flush=True)


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
    global AGENTS, _TOOL_CACHE, _PRESET_TOOL_CACHE, _PRESET_METADATA
    
    print("[Agent API] Initializing agent registry...", flush=True)
    
    # Discover built-in agents
    AGENTS = _discover_agents()
    print(f"[Agent API] Agent discovery complete. Found {len(AGENTS)} built-in agents.", flush=True)
    
    # Cache all tools for preset filtering
    try:
        from core.utils.tool_discovery import get_all_tools
        _TOOL_CACHE = get_all_tools()
        print("[Agent API] Tool cache initialized", flush=True)
    except Exception as e:
        print(f"[Agent API] WARNING: Failed to cache tools: {e}", flush=True)
        _TOOL_CACHE = {}
    
    # Load agent presets from master_config
    master_config_path = PROJECT_ROOT / "core" / "master_config.json"
    if master_config_path.exists():
        try:
            master_config = json.loads(master_config_path.read_text())
            agent_presets = master_config.get("agent_presets", {})
            
            for preset_name, preset_config in agent_presets.items():
                if not preset_config.get("enabled", True):
                    print(f"[Agent API] Skipping disabled preset: {preset_name}", flush=True)
                    continue
                
                base_agent = preset_config.get("base_agent")
                if base_agent not in AGENTS:
                    print(f"[Agent API] Skipping preset {preset_name}: base agent {base_agent} not found", flush=True)
                    continue
                
                # Register preset as model (points to same module as base agent)
                AGENTS[preset_name] = AGENTS[base_agent]
                AGENT_PATHS[preset_name] = f"preset:{base_agent}"
                
                # Cache enabled tools for this preset
                enabled_tool_names = {
                    name for name, cfg in preset_config.get("tool_config", {}).items()
                    if cfg.get("enabled", False)
                }
                _PRESET_TOOL_CACHE[preset_name] = enabled_tool_names
                
                # Store metadata for /v1/models endpoint
                _PRESET_METADATA[preset_name] = {
                    "base_agent": base_agent,
                    "tool_count": len(enabled_tool_names),
                    "is_preset": True
                }
                
                print(f"[Agent API] ✓ Registered preset: {preset_name} (base: {base_agent}, {len(enabled_tool_names)} tools)", flush=True)
            
            if agent_presets:
                print(f"[Agent API] Loaded {len(agent_presets)} agent preset(s)", flush=True)
        except Exception as e:
            print(f"[Agent API] WARNING: Failed to load agent presets: {e}", flush=True)
    
    # Warm agents if they expose initialize_runtime()
    for k, mod in AGENTS.items():
        # Skip warming for presets (they use the same runtime as base agent)
        if AGENT_PATHS.get(k, "").startswith("preset:"):
            continue
        
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
@app.get("/")
async def root():
    """Root endpoint with API information (no auth required)"""
    agent_list = list(AGENTS.keys()) if AGENTS else ["(discovering...)"]
    return {
        "message": "Luna Agent API - OpenAI compatible",
        "base_url": PUBLIC_URL,
        "endpoints": [
            "/v1/models",
            "/v1/chat/completions",
            "/extensions"
        ],
        "auth": "Bearer token required (use AGENT_API_KEY)",
        "available_agents": agent_list
    }

@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    """Health check endpoint (no auth required)."""
    return {"status": "ok"}


@app.get("/extensions")
async def list_extensions_status(api_key: str = Security(verify_api_key)) -> Dict[str, Any]:
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
async def get_extension_status(name: str, api_key: str = Security(verify_api_key)) -> Dict[str, Any]:
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
async def restart_extension_ui(name: str, api_key: str = Security(verify_api_key)) -> Dict[str, Any]:
    try:
        from core.utils.service_manager import get_manager
        mgr = get_manager()
        ok = mgr.restart_ui(name)
        if not ok:
            raise HTTPException(status_code=404, detail="ui not found")
        _trigger_caddy_reload(f"restart-ui:{name}")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="internal error")


@app.post("/extensions/{name}/services/{service}/restart")
async def restart_extension_service(name: str, service: str, api_key: str = Security(verify_api_key)) -> Dict[str, Any]:
    try:
        from core.utils.service_manager import get_manager
        mgr = get_manager()
        ok = mgr.restart_service(name, service)
        if not ok:
            raise HTTPException(status_code=404, detail="service not found")
        _trigger_caddy_reload(f"restart-service:{name}.{service}")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="internal error")


@app.get("/v1/models")
async def list_models(api_key: str = Security(verify_api_key)):
    """List available models (agents and presets)."""
    now = int(time.time())
    models = []
    
    for model_id in sorted(AGENTS.keys()):
        meta = _PRESET_METADATA.get(model_id, {})
        model_data = {
            "id": model_id,
            "object": "model",
            "created": now,
            "owned_by": "luna",
            "is_preset": meta.get("is_preset", False)
        }
        
        # Add preset-specific metadata
        if meta.get("is_preset"):
            model_data["base_agent"] = meta.get("base_agent")
            model_data["tool_count"] = meta.get("tool_count")
        
        models.append(model_data)
    
    return {"object": "list", "data": models}


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str, api_key: str = Security(verify_api_key)):
    """Get details of a specific model (agent)."""
    if model_id not in AGENTS:
        raise HTTPException(status_code=404, detail="model not found")
    return {"id": model_id, "object": "model", "created": int(time.time()), "owned_by": "luna"}


@app.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    response: Response,
    api_key: str = Security(verify_api_key),
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
    
    # Check if this is a preset and get tool filter
    is_preset = model_id in _PRESET_TOOL_CACHE
    allowed_tool_names = _PRESET_TOOL_CACHE.get(model_id) if is_preset else None
    
    if is_preset:
        print(f"[Agent API] Using preset '{model_id}' with {len(allowed_tool_names) if allowed_tool_names else 0} enabled tools", flush=True)
        # NOTE: Tool filtering for presets requires integration with the agent's tool discovery mechanism.
        # Currently, agents auto-discover all tools. To implement filtering, we would need to:
        # 1. Pass allowed_tool_names to agent's initialize_runtime() or run_agent()
        # 2. Modify extension_discovery to filter tools based on allowed list
        # 3. Or set a context variable that tool discovery checks
        # For now, presets are registered as models but use the same tools as base agents.

    chat_history, user_prompt = _split_history_and_prompt(body.messages)
    memory = _extract_memory(body.messages, memory_header)

    # Auto-fetch memories from database if not provided by client
    if not memory:
        try:
            from core.utils.db import get_db
            db = get_db()
            rows = db.execute("SELECT id, content FROM memories ORDER BY id ASC")
            if rows:
                memory_lines = [f"{i+1}. {row['content']}" for i, row in enumerate(rows)]
                memory = "\n".join(memory_lines)
                print(f"[Agent API] Auto-fetched {len(rows)} memories from database", flush=True)
        except Exception as e:
            print(f"[Agent API] Failed to auto-fetch memories: {e}", flush=True)

    # Debug logging
    print(f"[Agent API] Model: {model_id} | Is Preset: {is_preset}", flush=True)
    print(f"[Agent API] Extracted chat_history: {bool(chat_history)} (len={len(chat_history) if chat_history else 0})", flush=True)
    print(f"[Agent API] Extracted memory: {bool(memory)} (len={len(memory) if memory else 0})", flush=True)
    print(f"[Agent API] Memory header: {bool(memory_header)}", flush=True)
    if chat_history:
        print(f"[Agent API] Chat history preview: {chat_history[:200]}", flush=True)
    if memory:
        print(f"[Agent API] Memory preview: {memory[:200]}", flush=True)

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
    host = os.environ.get("AGENT_API_HOST", "127.0.0.1")
    port = int(os.environ.get("AGENT_API_PORT", "8080"))
    
    print("="*60)
    print("🌙 Luna Agent API Starting...")
    print("="*60)
    print(f"Public URL: {PUBLIC_URL}")
    print(f"API Key: {API_KEY}")
    print(f"Default Agent: {DEFAULT_AGENT}")
    print("\nEndpoints:")
    print(f"  - GET  {PUBLIC_URL}/v1/models")
    print(f"  - POST {PUBLIC_URL}/v1/chat/completions")
    print(f"  - GET  {PUBLIC_URL}/extensions")
    print("\nAuthentication:")
    print(f"  Add header: Authorization: Bearer {API_KEY}")
    print("="*60)
    print(f"\nStarting server on {host}:{port}...\n")
    
    uvicorn.run(app, host=host, port=port, reload=False)
