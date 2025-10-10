"""Simple ReAct agent implementation.

LangChain ReAct agent that discovers and uses all available tools from extensions.
Includes error retry logic (up to 2 retries on tool failures).
"""
import os
import sys
import json
import time
import inspect
from typing import Any, Dict, List, Optional, Tuple, get_type_hints
from pathlib import Path

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from pydantic import BaseModel, Field
from langchain_core.callbacks.base import BaseCallbackHandler
from core.utils.extension_discovery import discover_extensions
from core.utils.llm_selector import get_chat_model


# ---- Pydantic Models (I/O Contract) ----
class ToolTrace(BaseModel):
    """Record of a tool execution."""
    tool: str
    args: Optional[Dict[str, Any]] = None
    output: str
    duration_secs: Optional[float] = None


class Timing(BaseModel):
    """Timing information for an operation."""
    name: str
    seconds: float


class AgentResult(BaseModel):
    """Result from agent execution."""
    # Compatibility fields
    final: str
    results: List[Any] = Field(default_factory=list)
    timings: List[Timing] = Field(default_factory=list)
    # Spec fields
    content: str
    response_time_secs: float
    traces: List[ToolTrace] = Field(default_factory=list)


# ---- Runtime cache ----
PRELOADED_TOOLS: List[Any] = []
RUN_TRACES: List[ToolTrace] = []
DOMAIN_PROMPTS_TEXT: str = ""


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with fallback."""
    val = os.getenv(key)
    return val if isinstance(val, str) and val.strip() else default


def _wrap_callable_as_tool(fn, ext_name: str):
    """Wrap a Python callable as a LangChain StructuredTool with retry logic."""
    from langchain_core.tools import StructuredTool
    from pydantic import create_model

    # Get full docstring for agent visibility
    try:
        full_doc = inspect.getdoc(fn) or ""
    except Exception:
        full_doc = ""
    
    if full_doc.strip():
        description = full_doc.strip()
    else:
        # Fallback to function name
        description = fn.__name__

    # Build Pydantic schema for structured args
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
        """Runner with retry logic (up to 2 retries on failure)."""
        last_err = None
        for attempt in range(2):  # Try once, then retry once more
            try:
                t0 = time.perf_counter()
                result = fn(**kwargs)
                
                # Normalize result to string
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
                if attempt == 0:  # Retry once
                    continue
                # Final failure
                try:
                    dur = time.perf_counter() - t0  # type: ignore[name-defined]
                except Exception:
                    dur = None
                RUN_TRACES.append(ToolTrace(tool=fn.__name__, args=(kwargs or None), output=last_err, duration_secs=dur))
                return last_err
        
        return last_err or "Unknown error"

    return StructuredTool(name=fn.__name__, description=description, args_schema=ArgsSchema, func=_runner)


def initialize_runtime(tool_root: Optional[str] = None) -> None:
    """Initialize tools and system prompts from extensions."""
    global PRELOADED_TOOLS, DOMAIN_PROMPTS_TEXT
    
    try:
        exts = discover_extensions(tool_root)
    except Exception:
        exts = []
    
    tools: List[Any] = []
    domain_prompts: List[str] = []
    
    for ext in exts:
        for fn in (ext.get("tools") or []):
            try:
                tools.append(_wrap_callable_as_tool(fn, ext.get("name", "unknown")))
            except Exception:
                continue
        
        # Collect system prompts
        try:
            name = ext.get("name", "")
            sp = ext.get("system_prompt", "")
            if isinstance(name, str) and isinstance(sp, str) and sp.strip():
                domain_prompts.append(f"[Domain: {name}]\n{sp.strip()}")
        except Exception:
            pass
    
    PRELOADED_TOOLS = tools
    try:
        DOMAIN_PROMPTS_TEXT = "\n\n".join([p for p in domain_prompts if p])
    except Exception:
        DOMAIN_PROMPTS_TEXT = ""


def _active_models() -> Dict[str, str]:
    """Return active model configuration (for debugging/logging)."""
    return {"model": _get_env("LLM_DEFAULT_MODEL", "gpt-4.1") or "gpt-4.1"}


class LLMRunTracer(BaseCallbackHandler):
    """Callback handler to track LLM execution time."""
    
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


async def run_agent(
    user_prompt: str,
    chat_history: Optional[str] = None,
    memory: Optional[str] = None,
    tool_root: Optional[str] = None,
    llm: Optional[str] = None
) -> AgentResult:
    """Run the simple ReAct agent.
    
    Args:
        user_prompt: The user's prompt/query
        chat_history: Optional chat history context
        memory: Optional memory context (list of strings)
        tool_root: Optional custom tool discovery root
        llm: Optional LLM model override
        
    Returns:
        AgentResult with final response and execution details
    """
    # Initialize tools if needed
    if not PRELOADED_TOOLS or isinstance(tool_root, str):
        initialize_runtime(tool_root=tool_root)
    
    tools = PRELOADED_TOOLS or []
    if not tools:
        msg = "No tools discovered. Ensure files matching *_tools.py exist under extensions/."
        return AgentResult(final=msg, results=[], timings=[], content=msg, response_time_secs=0.0, traces=[])

    # Build ReAct agent
    try:
        from langgraph.prebuilt import create_react_agent
        
        model = get_chat_model(
            role="domain",
            model=llm or _get_env("LLM_DEFAULT_MODEL", "gpt-4.1"),
            callbacks=[LLMRunTracer("react")],
            temperature=0.0
        )
        
        # Include domain system prompts if available
        if isinstance(DOMAIN_PROMPTS_TEXT, str) and DOMAIN_PROMPTS_TEXT.strip():
            final_prompt = "Domain system prompts:\n" + DOMAIN_PROMPTS_TEXT.strip()
            agent = create_react_agent(model, tools=tools, prompt=final_prompt)
        else:
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
        result = await agent.ainvoke(
            {"messages": messages},
            config={"recursion_limit": 16, "callbacks": [LLMRunTracer("react")]}
        )
    except RuntimeError:
        # Fallback for event loop issues
        loop = asyncio.get_event_loop()
        result = await agent.ainvoke(
            {"messages": messages},
            config={"recursion_limit": 16, "callbacks": [LLMRunTracer("react")]}
        )
    
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

    # Assemble response
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


async def run_agent_stream(
    user_prompt: str,
    chat_history: Optional[str] = None,
    memory: Optional[str] = None,
    tool_root: Optional[str] = None,
    llm: Optional[str] = None
):
    """Stream incremental text chunks while the agent generates a response.
    
    Yields:
        String tokens as they are generated
    """
    # Initialize tools if needed
    if not PRELOADED_TOOLS or isinstance(tool_root, str):
        initialize_runtime(tool_root=tool_root)
    
    tools = PRELOADED_TOOLS or []
    if not tools:
        yield "No tools discovered. Ensure files matching *_tools.py exist under extensions/."
        return

    # Build ReAct agent
    try:
        from langgraph.prebuilt import create_react_agent
        
        model = get_chat_model(
            role="domain",
            model=llm or _get_env("LLM_DEFAULT_MODEL", "gpt-4.1"),
            callbacks=[LLMRunTracer("react")],
            temperature=0.0
        )
        
        if isinstance(DOMAIN_PROMPTS_TEXT, str) and DOMAIN_PROMPTS_TEXT.strip():
            final_prompt = "Domain system prompts:\n" + DOMAIN_PROMPTS_TEXT.strip()
            agent = create_react_agent(model, tools=tools, prompt=final_prompt)
        else:
            agent = create_react_agent(model, tools=tools)
    
    except Exception:
        # Fallback to non-streaming
        res = await run_agent(user_prompt, chat_history=chat_history, memory=memory, tool_root=tool_root, llm=llm)
        yield res.final
        return

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

    # Clear traces
    del RUN_TRACES[:]

    yielded_any = False
    try:
        # Stream events for token-by-token output
        async for event in agent.astream_events(
            {"messages": messages},
            config={"recursion_limit": 16, "callbacks": [LLMRunTracer("react")]},
            version="v1"
        ):
            try:
                ev = event.get("event") if isinstance(event, dict) else getattr(event, "event", None)
                if ev == "on_chat_model_stream":
                    data = event.get("data") if isinstance(event, dict) else getattr(event, "data", {})
                    chunk = (data or {}).get("chunk") if isinstance(data, dict) else getattr(data, "chunk", None)
                    content = getattr(chunk, "content", None)
                    
                    # Handle both string (OpenAI) and list (Anthropic) content
                    text = None
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list) and content:
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text = item.get("text", "")
                                break
                    
                    if text:
                        yielded_any = True
                        yield text
            except Exception:
                continue
    except Exception:
        pass

    if not yielded_any:
        # Fallback to non-streaming
        res = await run_agent(user_prompt, chat_history=chat_history, memory=memory, tool_root=tool_root, llm=llm)
        yield res.final


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for testing."""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Simple ReAct agent")
    parser.add_argument("-p", "--prompt", type=str, default="what can you do?", help="Test prompt")
    parser.add_argument("-r", "--tool-root", type=str, default=None, help="Tool discovery root")
    args = parser.parse_args(argv)
    
    try:
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

