import argparse
import asyncio
import json
import os
import sys
from typing import List, Dict, Any
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore

# Allow running both as a module and as a script
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.agent.orchestrator_local import orchestrate
from core.agent.agents_local import DEFAULT_MODEL_NAME


def _json_default(obj):
    """Best-effort serializer for non-JSON types (e.g., LangChain messages)."""
    # LangChain message objects (AIMessage, HumanMessage, ToolMessage, etc.)
    try:
        from langchain_core.messages import BaseMessage  # type: ignore
        if isinstance(obj, BaseMessage):
            # Convert to a lightweight, JSON-friendly representation
            data = {
                "type": obj.__class__.__name__,
                "content": getattr(obj, "content", None),
            }
            # Common optional attributes – include when present
            for attr in (
                "name",
                "tool_call_id",
                "tool_calls",
                "additional_kwargs",
                "response_metadata",
            ):
                if hasattr(obj, attr):
                    data[attr] = getattr(obj, attr)
            return data
    except Exception:
        pass

    # Pydantic models
    try:
        from pydantic import BaseModel  # type: ignore
        if isinstance(obj, BaseModel):
            try:
                return obj.model_dump()  # pyright: ignore[reportAttributeAccessIssue]
            except Exception:
                return obj.dict()  # type: ignore[attr-defined]
    except Exception:
        pass

    # Dataclasses
    try:
        import dataclasses  # type: ignore
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
    except Exception:
        pass

    # Bytes/bytearray → utf-8 string (best effort)
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8")
        except Exception:
            return obj.decode("utf-8", "replace")

    # Sets → lists
    if isinstance(obj, set):
        return list(obj)

    # Fallback: string representation
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def _extract_text(result: Dict[str, Any]) -> str:
    """Extract a final assistant text from orchestrator result."""
    synth = (result or {}).get("synth") or {}
    out = synth.get("output")
    if isinstance(out, str) and out.strip():
        return out.strip()
    out = (result or {}).get("final_output")
    if isinstance(out, str) and out.strip():
        return out.strip()
    return str(result)


def _build_user_input_with_history(history: List[Dict[str, str]], new_user_text: str) -> str:
    """Compose a user input string augmented with prior conversation for context.

    Follows the same formatting used by the local OpenAI-compatible API server
    ("Previous conversation:" lines and a final "Current message:").
    """
    new_user_text = (new_user_text or "").strip()
    if not history:
        return new_user_text

    ctx: List[str] = ["Previous conversation:"]
    for m in history:
        c = (m.get("content") or "").strip()
        if not c:
            continue
        role = m.get("role") or ""
        if role == "user":
            who = "User"
        elif role == "assistant":
            who = "Assistant"
        else:
            who = role.capitalize() if role else "Message"
        ctx.append(f"{who}: {c}")
    ctx.append("")
    ctx.append(f"Current message: {new_user_text}")
    return "\n".join(ctx)


def main() -> None:
    parser = argparse.ArgumentParser(description="Direct Local Agents Chat (GeneralByte + HomeAssistant)")
    parser.add_argument("--once", type=str, default=None, help="Run a single prompt and exit")
    args = parser.parse_args()

    if load_dotenv is not None:
        load_dotenv()
    try:
        print(f"Active model: {DEFAULT_MODEL_NAME}")
    except Exception:
        pass

    if args.once is not None:
        # One-shot, no session memory
        out = asyncio.run(orchestrate(args.once))
        print(json.dumps(out, indent=2, default=_json_default))
        return

    # Interactive mode with in-memory per-session history
    print("Direct chat ready. Type 'exit' to quit.")
    messages: List[Dict[str, str]] = []  # [{role: user|assistant, content: str}]
    MAX_HISTORY = 25
    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input.strip():
            continue
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        try:
            # Build contextual input using prior turns
            composed = _build_user_input_with_history(messages, user_input)
            out = asyncio.run(orchestrate(composed))
        except Exception as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            continue
        print(json.dumps(out, indent=2, default=_json_default))

        # Update in-memory history with this user turn and assistant reply
        try:
            assistant_text = _extract_text(out)
        except Exception:
            assistant_text = ""
        messages.append({"role": "user", "content": user_input})
        if assistant_text:
            messages.append({"role": "assistant", "content": assistant_text})
        # Trim to last MAX_HISTORY entries
        if len(messages) > MAX_HISTORY:
            messages = messages[-MAX_HISTORY:]


if __name__ == "__main__":
    main()


