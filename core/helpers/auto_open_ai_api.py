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

from fastapi import FastAPI, Response, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure project root on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Optional .env
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# ---- Config ----
DEBUG = os.getenv("OPENAI_COMPAT_DEBUG", "true").lower() in ("1", "true", "yes", "on")
# No auth per user request

# Default selected agent (model) if request.model is omitted
DEFAULT_AGENT = os.getenv("OPENAI_DEFAULT_AGENT", "parallel_agent")

# Discovery config
# Comma-separated globs, resolved relative to PROJECT_ROOT
DISCOVERY_GLOBS = os.getenv(
    "OPENAI_AGENT_SEARCH_GLOBS",
    "core/agent/*.py",
).split(",")

# Skip files by basename during discovery
SKIP_BASENAMES = set({
    "__init__.py",
    os.path.basename(__file__),  # this server module
})

app = FastAPI(title="Luna OpenAI-compatible API (Multi-Agent, No Auth)")

# ---- Request models ----
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(default=None)
    messages: List[ChatMessage]
    stream: Optional[bool] = Field(default=False)
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    n: Optional[int] = Field(default=1)


# ---- Registry ----
AGENTS: Dict[str, ModuleType] = {}
AGENT_PATHS: Dict[str, str] = {}


def _split_history_and_prompt(messages: List[ChatMessage]) -> Tuple[str, str]:
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
        else:
            # ignore system/tool/function in chat_history
            continue
    return "\n".join(lines), last_user_text


def _extract_memory(messages: List[ChatMessage], header_memory: Optional[str]) -> Optional[str]:
    # Intentionally ignore system messages for memory; only honor X-Luna-Memory header
    if header_memory and header_memory.strip():
        return header_memory.strip()
    return None


def _make_chat_completion_payload(model: str, content: str) -> Dict[str, Any]:
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


async def _sse_token_stream(mod: ModuleType, user_prompt: str, chat_history: Optional[str], memory: Optional[str], model_id: str) -> AsyncGenerator[str, None]:
    """Stream token-by-token SSE compatible with OpenAI Chat Completions.

    Requires the module to expose `run_agent_stream` as an async generator yielding strings.
    Falls back to a single final chunk if streaming fails.
    """
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

    # Close out the stream. If we didn't yield anything, send an empty content chunk for compatibility
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
    fn = getattr(mod, "run_agent", None)
    return inspect.iscoroutinefunction(fn)


def _import_module_from_path(path: str) -> Optional[ModuleType]:
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
    found: Dict[str, ModuleType] = {}
    for pat in DISCOVERY_GLOBS:
        pat = pat.strip()
        if not pat:
            continue
        full_pat = os.path.join(PROJECT_ROOT, pat) if not os.path.isabs(pat) else pat
        for file_path in glob.glob(full_pat, recursive=True):
            base = os.path.basename(file_path)
            if base in SKIP_BASENAMES or not base.endswith(".py"):
                continue
            mod = _import_module_from_path(file_path)
            if not mod:
                continue
            if not _is_async_run_agent(mod):
                continue
            model_id = os.path.splitext(base)[0]
            found[model_id] = mod
            AGENT_PATHS[model_id] = os.path.relpath(file_path, PROJECT_ROOT)
    return found


def _maybe_print_startup_models() -> None:
    if not DEBUG:
        return
    try:
        print("Discovered agents:")
        for k, mod in AGENTS.items():
            line = f"- {k}"
            ap = getattr(mod, "_active_models", None)
            if callable(ap):
                try:
                    detail = ap()
                    line += f" | active_models={detail}"
                except Exception:
                    pass
            p = AGENT_PATHS.get(k)
            if p:
                line += f" | path={p}"
            print(line)
        print("")
    except Exception:
        pass


def _init_agents() -> None:
    global AGENTS
    AGENTS = _discover_agents()
    # Warm agents if they expose initialize_runtime()
    for k, mod in AGENTS.items():
        init = getattr(mod, "initialize_runtime", None)
        if callable(init):
            try:
                init()
            except Exception:
                # warming is best-effort
                pass


# ---- Lifecycle ----
@app.on_event("startup")
async def _on_startup() -> None:
    _init_agents()
    _maybe_print_startup_models()


# ---- Routes ----
@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models():
    now = int(time.time())
    data = [{"id": mid, "object": "model", "created": now, "owned_by": "luna"} for mid in sorted(AGENTS.keys())]
    return {"object": "list", "data": data}


@app.get("/v1/models/{model_id}")
async def get_model(model_id: str):
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
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    model_id = (body.model or "").strip() or DEFAULT_AGENT
    mod = AGENTS.get(model_id)
    if not mod:
        # refresh once in case of hot add
        _init_agents()
        mod = AGENTS.get(model_id)
        if not mod:
            raise HTTPException(status_code=404, detail=f"unknown model '{model_id}'")

    chat_history, user_prompt = _split_history_and_prompt(body.messages)
    memory = _extract_memory(body.messages, memory_header)

    # Streaming path with token-by-token support when available
    if body.stream:
        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
        try:
            # Prefer token streaming if the agent provides run_agent_stream
            if hasattr(mod, "run_agent_stream"):
                return StreamingResponse(
                    _sse_token_stream(mod, user_prompt, chat_history or None, memory, model_id),
                    media_type="text/event-stream",
                    headers=headers,
                )
        except Exception:
            # Fall through to one-shot stream below
            pass

        # Fallback: compute final text once and stream in a single chunk
        try:
            result_fallback = await mod.run_agent(user_prompt, chat_history=chat_history or None, memory=memory)  # type: ignore[attr-defined]
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"agent error: {exc}") from exc
        final_text_fallback: str = str(getattr(result_fallback, "final", result_fallback))
        return StreamingResponse(_sse_gen(final_text_fallback, model_id), media_type="text/event-stream", headers=headers)

    # Non-streaming path
    try:
        t0 = time.perf_counter()
        result = await mod.run_agent(user_prompt, chat_history=chat_history or None, memory=memory)  # type: ignore[attr-defined]
        elapsed = round(time.perf_counter() - t0, 3)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"agent error: {exc}") from exc

    final_text: str = str(getattr(result, "final", result))

    # Timings header
    timings_list = []
    try:
        for tm in getattr(result, "timings", []) or []:
            timings_list.append({"name": getattr(tm, "name", "unknown"), "seconds": getattr(tm, "seconds", None)})
    except Exception:
        pass
    timing_header = {"steps": timings_list, "server_elapsed_s": elapsed, "agent": model_id}
    response.headers["X-Luna-Timings"] = json.dumps(timing_header)

    payload = _make_chat_completion_payload(model_id, final_text)
    return JSONResponse(content=payload)


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8069"))
    uvicorn.run(app, host=host, port=port, reload=False)


