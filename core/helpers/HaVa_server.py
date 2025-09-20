import os
import sys
import time
import uuid
import json
from typing import List, Optional, Literal, Dict, Any, Tuple, AsyncGenerator

from fastapi import FastAPI, Response, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure project root on sys.path for absolute imports when running as a script
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Optional .env
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

# Resolve active agent module from env path (defaults to parallel_agent)
ACTIVE_AGENT_PATH = os.getenv("ACTIVE_AGENT_PATH", "core/agent/parallel_agent.py")

def _import_agent_from_path(path: str):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, os.path.join(PROJECT_ROOT, path))
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod
    except Exception:
        # Fallback to built-in parallel agent
        from core.agent import parallel_agent as fallback

        return fallback

pa = _import_agent_from_path(ACTIVE_AGENT_PATH)


# Config
# Toggle detailed debug printing (same as original agent CLI)
# Set to True to enable verbose debug logs
DEBUG = True
API_KEY_REQUIRED = os.getenv("OPENAI_COMPAT_API_KEY")  # set to require Bearer
DEFAULT_MODEL_ID = os.getenv("OPENAI_COMPAT_MODEL_ID", "luna-hava")

app = FastAPI(title="HaVa OpenAI-compatible Chat API (Luna Parallel Agent)")


# ---- Schemas ----
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


# ---- Helpers ----
def _require_auth(authorization: Optional[str]) -> None:
    if not API_KEY_REQUIRED:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_KEY_REQUIRED:
        raise HTTPException(status_code=401, detail="invalid api key")


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
            # ignore system/tool/function in chat_history; handled as memory/system elsewhere
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
        "model": model or DEFAULT_MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _maybe_print_startup_models() -> None:
    if not DEBUG:
        return
    try:
        print(f"Active agent path: {ACTIVE_AGENT_PATH}")
        models = pa._active_models()
        print(
            f"Active models: router={models.get('router')} | domain={models.get('domain')} | synth={models.get('synth')}"
        )
        print("")
    except Exception:
        pass


def _print_agent_debug(ret: Any) -> None:
    if not DEBUG:
        return
    try:
        if isinstance(ret, pa.AgentResult):
            results = ret.results or []
            report_lines: List[str] = []
            for dr in results:
                traces = dr.traces or []
                report_lines.append(f"Domain: {dr.name}")
                if dr.intent:
                    report_lines.append(f"Intent: {dr.intent}")
                if dr.duration_secs is not None:
                    try:
                        report_lines.append(f"Duration: {float(dr.duration_secs):.2f}s")
                    except Exception:
                        report_lines.append(f"Duration: {dr.duration_secs}")
                for t in traces:
                    report_lines.append(f"- {t.tool}")
                    try:
                        args_str = json.dumps(t.args, ensure_ascii=False)
                    except Exception:
                        args_str = str(t.args)
                    report_lines.append(f"  args: {args_str}")
                    report_lines.append(f"  output: {t.output}")
                report_lines.append("")
            if report_lines:
                print("\n".join(report_lines).strip())
                print("\n---\n")
            print(ret.final)
            if ret.timings:
                print("\nTimings:")
                for tm in ret.timings:
                    try:
                        secs = float(tm.seconds)
                        print(f"- {tm.name}: {secs:.2f}s")
                    except Exception:
                        print(f"- {tm.name}: {tm.seconds}")
        else:
            print(str(ret))
    except Exception:
        # Keep server responses unaffected by debug printing failures
        pass


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


# ---- Lifecycle ----
@app.on_event("startup")
async def _on_startup() -> None:
    try:
        pa.initialize_runtime()
    except Exception:
        # Non-fatal; runtime will lazy-initialize
        pass
    _maybe_print_startup_models()


# ---- Routes ----
@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models(authorization: Optional[str] = Header(default=None)):
    _require_auth(authorization)
    return {"object": "list", "data": [{"id": DEFAULT_MODEL_ID, "object": "model"}]}


@app.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    response: Response,
    authorization: Optional[str] = Header(default=None),
    memory_header: Optional[str] = Header(default=None, alias="X-Luna-Memory"),
):
    _require_auth(authorization)
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    chat_history, user_prompt = _split_history_and_prompt(body.messages)
    memory = _extract_memory(body.messages, memory_header)

    # Call agent
    try:
        t0 = time.perf_counter()
        result = await pa.run_agent(user_prompt, chat_history=chat_history or None, memory=memory)
        elapsed = round(time.perf_counter() - t0, 3)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"agent error: {exc}") from exc

    final_text: str
    if hasattr(result, "final"):
        final_text = str(getattr(result, "final"))
    else:
        final_text = str(result)

    # Debug print mirroring original agent CLI output
    _print_agent_debug(result)

    timings_list = []
    try:
        for tm in getattr(result, "timings", []) or []:
            timings_list.append({"name": getattr(tm, "name", "unknown"), "seconds": getattr(tm, "seconds", None)})
    except Exception:
        pass
    timing_header = {"steps": timings_list, "server_elapsed_s": elapsed}
    response.headers["X-Luna-Timings"] = json.dumps(timing_header)

    model_id = body.model or DEFAULT_MODEL_ID

    if body.stream:
        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Luna-Timings": json.dumps(timing_header),
        }
        return StreamingResponse(_sse_gen(final_text, model_id), media_type="text/event-stream", headers=headers)

    payload = _make_chat_completion_payload(model_id, final_text)
    return JSONResponse(content=payload)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run(app, host=host, port=port, reload=False)


