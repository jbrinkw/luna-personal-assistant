import os
import sys
import time
import uuid
import json
from typing import List, Optional, Literal, Dict, Any, AsyncGenerator

from fastapi import FastAPI, Response, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field

# ---- local orchestrator import path tweak ----
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.agent.orchestrator_local import orchestrate

# Optional .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

API_KEY_REQUIRED = os.getenv("OPENAI_COMPAT_API_KEY")       # set to require Bearer
DEFAULT_MODEL_ID = os.getenv("OPENAI_COMPAT_MODEL_ID", "luna-orchestrator")

app = FastAPI(title="OpenAI-compatible Chat API (Luna Local Orchestrator)")

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
def _require_auth(authorization: Optional[str]):
    if not API_KEY_REQUIRED:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_KEY_REQUIRED:
        raise HTTPException(status_code=401, detail="invalid api key")

def _build_user_input(messages: List[ChatMessage]) -> str:
    user_indexes = [i for i, m in enumerate(messages) if m.role == "user" and (m.content or "").strip()]
    if not user_indexes:
        raise HTTPException(status_code=400, detail="no user message provided")
    last_user_idx = user_indexes[-1]
    last_user_text = (messages[last_user_idx].content or "").strip()

    prior = messages[:last_user_idx]
    if not prior:
        return last_user_text

    ctx: List[str] = ["Previous conversation:"]
    for m in prior:
        c = (m.content or "").strip()
        if not c:
            continue
        role = "User" if m.role == "user" else "Assistant" if m.role == "assistant" else m.role.capitalize()
        ctx.append(f"{role}: {c}")
    ctx.append("")
    ctx.append(f"Current message: {last_user_text}")
    return "\n".join(ctx)

def _extract_text(result: Dict[str, Any]) -> str:
    synth = (result or {}).get("synth") or {}
    out = synth.get("output")
    if isinstance(out, str) and out.strip():
        return out.strip()
    out = (result or {}).get("final_output")
    if isinstance(out, str) and out.strip():
        return out.strip()
    return str(result)

def _make_chat_completion_payload(model: str, content: str) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model or DEFAULT_MODEL_ID,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

async def _sse_gen(final_text: str, model_id: str) -> AsyncGenerator[str, None]:
    cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    chunk1 = {
        "id": cid, "object": "chat.completion.chunk", "created": created, "model": model_id,
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": final_text}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(chunk1)}\n\n"
    chunk2 = {
        "id": cid, "object": "chat.completion.chunk", "created": created, "model": model_id,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(chunk2)}\n\n"
    yield "data: [DONE]\n\n"

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
):
    _require_auth(authorization)
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    user_input = _build_user_input(body.messages)

    # Call orchestrator
    try:
        t0 = time.perf_counter()
        result: Dict[str, Any] = await orchestrate(user_input)
        elapsed = round(time.perf_counter() - t0, 3)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"orchestrator error: {exc}") from exc

    final_text = _extract_text(result)
    timings = (result.get("timings") or {})
    timings = {**timings, "server_elapsed_s": elapsed}
    response.headers["X-Luna-Timings"] = json.dumps(timings)

    model_id = body.model or DEFAULT_MODEL_ID

    if body.stream:
        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Luna-Timings": json.dumps(timings),
        }
        return StreamingResponse(_sse_gen(final_text, model_id), media_type="text/event-stream", headers=headers)

    payload = _make_chat_completion_payload(model_id, final_text)
    return JSONResponse(content=payload)

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run(app, host=host, port=port, reload=False)
