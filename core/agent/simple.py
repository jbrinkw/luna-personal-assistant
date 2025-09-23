import os
import sys
import json
import time
import inspect
from typing import Any, Dict, List, Optional, Tuple, get_type_hints

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

from pydantic import BaseModel, Field
from langchain_core.callbacks.base import BaseCallbackHandler
from core.helpers.light_schema_gen import discover_extensions  # noqa: E402
from core.helpers.llm_selector import get_chat_model  # noqa: E402


# ---- Minimal spec models (with compatibility fields) ----
class ToolTrace(BaseModel):
    tool: str
    args: Optional[Dict[str, Any]] = None
    output: str
    duration_secs: Optional[float] = None


class Timing(BaseModel):
    name: str
    seconds: float


class AgentResult(BaseModel):
    # Compatibility with existing callers
    final: str
    results: List[Any] = Field(default_factory=list)
    timings: List[Timing] = Field(default_factory=list)
    # Minimal spec fields
    content: str
    response_time_secs: float
    traces: List[ToolTrace] = Field(default_factory=list)


# ---- Runtime cache ----
PRELOADED_TOOLS: List[Any] = []
RUN_TRACES: List[ToolTrace] = []


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    return val if isinstance(val, str) and val.strip() else default


def _wrap_callable_as_tool(fn, ext_name: str):
    from langchain_core.tools import StructuredTool
    from pydantic import create_model

    # Prefer full docstring so the agent sees complete instructions
    try:
        full_doc = inspect.getdoc(fn) or ""
    except Exception:
        full_doc = ""
    if full_doc.strip():
        description = full_doc.strip()
    else:
        # Fallback to summary + first non-empty example line
        doc = inspect.getdoc(fn) or ""
        lines = doc.splitlines()
        summary = lines[0].strip() if lines else ""
        example = ""
        for idx in range(1, len(lines)):
            ln = lines[idx].strip()
            if ln:
                example = ln
                break
        description = summary
        if example:
            description = f"{summary} Example: {example}"

    # Structured args schema (resolve forward refs like Optional[str])
    sig = inspect.signature(fn)
    fields: Dict[str, Tuple[Any, Any]] = {}
    try:
        hints = get_type_hints(fn, globalns=getattr(fn, "__globals__", {}))
    except Exception:
        hints = {}
    for name, param in sig.parameters.items():
        ann = hints.get(name, (param.annotation if param.annotation is not inspect._empty else str))
        default = param.default if param.default is not inspect._empty else ...
        fields[name] = (ann, default)
    ArgsSchema = create_model(f"{fn.__name__}Args", **fields)  # type: ignore[arg-type]

    def _runner(**kwargs):
        last_err = None
        for attempt in range(2):
            try:
                t0 = time.perf_counter()
                result = fn(**kwargs)
                # Normalize to string
                if isinstance(result, BaseModel):
                    try:
                        sres = json.dumps(result.model_dump(), ensure_ascii=False)
                    except Exception:
                        try:
                            sres = result.model_dump_json()
                        except Exception:
                            sres = result.json() if hasattr(result, "json") else str(result)
                elif isinstance(result, (dict, list)):
                    try:
                        sres = json.dumps(result, ensure_ascii=False)
                    except Exception:
                        sres = str(result)
                else:
                    sres = str(result)
                dur = time.perf_counter() - t0
                RUN_TRACES.append(ToolTrace(tool=fn.__name__, args=(kwargs or None), output=sres, duration_secs=dur))
                return sres
            except Exception as e:
                last_err = f"Error running tool {fn.__name__}: {str(e)}"
                if attempt == 0:
                    continue
                try:
                    dur = time.perf_counter() - t0  # type: ignore[name-defined]
                except Exception:
                    dur = None
                RUN_TRACES.append(ToolTrace(tool=fn.__name__, args=(kwargs or None), output=last_err, duration_secs=dur))
                return last_err

    return StructuredTool(name=fn.__name__, description=description, args_schema=ArgsSchema, func=_runner)


def initialize_runtime(tool_root: Optional[str] = None) -> None:
    global PRELOADED_TOOLS
    try:
        exts = discover_extensions(tool_root)
    except Exception:
        exts = []
    tools: List[Any] = []
    for ext in exts:
        for fn in (ext.get("tools") or []):
            try:
                tools.append(_wrap_callable_as_tool(fn, ext.get("name", "unknown")))
            except Exception:
                continue
    PRELOADED_TOOLS = tools


def _active_models() -> Dict[str, str]:
    # Minimal stub to keep CLI/server banners happy
    return {}


class LLMRunTracer(BaseCallbackHandler):
    def __init__(self, key: str):
        self.key = key
        self._starts: Dict[str, float] = {}

    def on_llm_start(self, serialized, prompts, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
        try:
            self._starts[str(run_id)] = time.perf_counter()
        except Exception:
            pass

    def on_llm_end(self, response, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
        try:
            self._starts.pop(str(run_id), None)
        except Exception:
            pass


async def run_agent(user_prompt: str, chat_history: Optional[str] = None, memory: Optional[str] = None, tool_root: Optional[str] = None, llm: Optional[str] = None) -> AgentResult:
    # Discover/warm tools if not already done or if tool_root differs
    if not PRELOADED_TOOLS or isinstance(tool_root, str):
        initialize_runtime(tool_root=tool_root)
    tools = PRELOADED_TOOLS or []
    if not tools:
        msg = "No tools discovered. Ensure files matching *_tool.py exist under extensions/."
        return AgentResult(final=msg, results=[], timings=[], content=msg, response_time_secs=0.0, traces=[])

    # Build a simple ReAct agent with all tools
    try:
        from langgraph.prebuilt import create_react_agent
        # Use tier if provided; else fall back to env model
        model = (
            get_chat_model(role="domain", tier=llm, callbacks=[LLMRunTracer("react")], temperature=0.0)
            if isinstance(llm, str) and llm.strip() in {"low", "med", "high"}
            else get_chat_model(role="domain", model=_get_env("REACT_MODEL", "gpt-4.1"), callbacks=[LLMRunTracer("react")], temperature=0.0)
        )
        agent = create_react_agent(model, tools=tools)
    except Exception as e:
        msg = f"Error building ReAct agent: {str(e)}"
        return AgentResult(final=msg, results=[], timings=[], content=msg, response_time_secs=0.0, traces=[])

    # Prepare messages
    from langchain_core.messages import SystemMessage, HumanMessage
    messages: List[Any] = []
    if chat_history or memory:
        messages.append(SystemMessage(content=(
            "Conversation context to consider when responding.\n"
            f"Chat history:\n{chat_history or ''}\n\n"
            f"Memory:\n{memory or ''}"
        )))
    messages.append(HumanMessage(content=user_prompt))

    # Clear traces for this run
    del RUN_TRACES[:]

    # Invoke agent
    import asyncio
    t0 = time.perf_counter()
    try:
        result = await agent.ainvoke({"messages": messages}, config={"recursion_limit": 8, "callbacks": [LLMRunTracer("react")]})
    except RuntimeError:
        # fallback loop handling if needed
        loop = asyncio.get_event_loop()
        result = await agent.ainvoke({"messages": messages}, config={"recursion_limit": 8, "callbacks": [LLMRunTracer("react")]})
    elapsed = time.perf_counter() - t0

    # Extract final content
    final_text: str
    try:
        msgs = result.get("messages") if isinstance(result, dict) else None
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            content = getattr(last, "content", None)
            final_text = content if isinstance(content, str) else str(result)
        else:
            final_text = str(result)
    except Exception:
        final_text = str(result)

    # Assemble timings and traces (minimal spec)
    timings = [Timing(name="total", seconds=float(elapsed))]
    traces = list(RUN_TRACES)

    return AgentResult(
        final=final_text,
        results=[],
        timings=timings,
        content=final_text,
        response_time_secs=float(elapsed),
        traces=traces,
    )


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Simple ReAct agent over all tools")
    parser.add_argument("-p", "--prompt", type=str, default="what can you do?", help="Test prompt")
    parser.add_argument("-r", "--tool-root", type=str, default=None, help="Optional root directory to discover tools under")
    args = parser.parse_args(argv)
    try:
        import asyncio
        ret = asyncio.run(run_agent(args.prompt, tool_root=args.tool_root))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        ret = loop.run_until_complete(run_agent(args.prompt, tool_root=args.tool_root))
    print(ret.final)
    if ret.traces:
        print("\nTools used:")
        for t in ret.traces:
            print(f"- {t.tool}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))



