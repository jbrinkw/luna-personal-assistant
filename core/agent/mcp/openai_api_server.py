import asyncio
import os
import time
import uuid
from typing import List, Optional, Literal, Dict, Any

from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel, Field

from standalone_orchestrator import orchestrate

# Optional: load environment variables from .env
try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


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


class ChatMessageOut(BaseModel):
    role: Literal["assistant"]
    content: str


class ChoiceOut(BaseModel):
    index: int
    message: ChatMessageOut
    finish_reason: Literal["stop"] = "stop"


class UsageOut(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionOut(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChoiceOut]
    usage: UsageOut


app = FastAPI(title="OpenAI-compatible Chat API (Luna Orchestrator)")


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(body: ChatCompletionRequest, response: Response) -> str:
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    # Build a conversation-aware prompt similar to previous test proxy behavior.
    # We will incorporate prior messages as context and treat the last user message
    # as the current instruction.
    all_msgs = body.messages
    user_indexes = [i for i, m in enumerate(all_msgs) if m.role == "user" and (m.content or "").strip()]
    if not user_indexes:
        raise HTTPException(status_code=400, detail="no user message provided")
    last_user_idx = user_indexes[-1]
    last_user_text = (all_msgs[last_user_idx].content or "").strip()

    prior = all_msgs[:last_user_idx]
    if prior:
        context_lines: list[str] = ["Previous conversation:"]
        for m in prior:
            content = (m.content or "").strip()
            if not content:
                continue
            if m.role == "user":
                role = "User"
            elif m.role == "assistant":
                role = "Assistant"
            elif m.role == "system":
                role = "System"
            else:
                role = m.role.capitalize()
            context_lines.append(f"{role}: {content}")
        context_lines.append("")
        context_lines.append(f"Current message: {last_user_text}")
        user_input = "\n".join(context_lines)
    else:
        user_input = last_user_text

    try:
        start = time.perf_counter()
        result: Dict[str, Any] = await orchestrate(user_input)
        elapsed = time.perf_counter() - start
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"orchestrator error: {exc}") from exc

    final_text = str(result.get("final_output") or "").strip()
    if not final_text:
        # Fallback: stringify the results when no final text is available
        final_text = str(result)

    # Expose orchestrator timings in a response header for debugging (without breaking OpenAI schema)
    timings = result.get("timings") or {}
    timings = {**timings, "server_elapsed_s": round(elapsed, 3)}
    try:
        import json as _json

        response.headers["X-Luna-Timings"] = _json.dumps(timings)
    except Exception:
        # If the header is too large or serialization fails, skip silently
        pass

    return final_text


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    # Run single-process async server; FastAPI handlers are async and support concurrency.
    uvicorn.run(app, host=host, port=port, reload=False)


