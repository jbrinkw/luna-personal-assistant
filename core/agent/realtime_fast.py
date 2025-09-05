import os
import sys
import json
import argparse
import asyncio
import inspect
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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

from core.helpers.light_schema_gen import discover_extensions, build_light_schema_for_extension  # noqa: E402
from core.helpers.llm_selector import get_chat_model  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from langchain_core.callbacks.base import BaseCallbackHandler  # noqa: E402


# ---- Minimal helpers (date prefix, tool wrapping) ----
def _current_date_line() -> str:
    try:
        return f"Date: {datetime.now().strftime('%Y-%m-%d')}"
    except Exception:
        return f"Date: {time.strftime('%Y-%m-%d')}"


def _with_date_prefix(content: str) -> str:
    return f"{_current_date_line()}\n{content}" if content else _current_date_line()


def _doc_summary_and_example(fn) -> Dict[str, str]:
    doc = inspect.getdoc(fn) or ""
    lines = doc.splitlines()
    summary = lines[0].strip() if lines else ""
    example = ""
    for idx in range(1, len(lines)):
        ln = lines[idx].strip()
        if ln:
            example = ln
            break
    return {"summary": summary, "example": example}


def _wrap_callable_as_tool(fn, ext_name: str):
    from langchain_core.tools import StructuredTool
    from pydantic import create_model

    meta = _doc_summary_and_example(fn)
    description = meta["summary"]
    if meta["example"]:
        description = f"{description} Example: {meta['example']}"

    sig = inspect.signature(fn)
    fields: Dict[str, Tuple[Any, Any]] = {}
    for name, param in sig.parameters.items():
        ann = param.annotation if param.annotation is not inspect._empty else str
        default = param.default if param.default is not inspect._empty else ...
        fields[name] = (ann, default)
    ArgsSchema = create_model(f"{fn.__name__}Args", **fields)  # type: ignore[arg-type]

    def _runner(**kwargs):
        try:
            result = fn(**kwargs)
            # normalize to string for LLM context
            if isinstance(result, BaseModel):
                try:
                    sres = json.dumps(result.model_dump(), ensure_ascii=False)
                except Exception:
                    sres = result.json() if hasattr(result, "json") else str(result)
            elif isinstance(result, (dict, list)):
                try:
                    sres = json.dumps(result, ensure_ascii=False)
                except Exception:
                    sres = str(result)
            else:
                sres = str(result)
            return sres
        except Exception as e:
            return f"Error running tool {fn.__name__}: {str(e)}"

    return StructuredTool(name=fn.__name__, description=description, args_schema=ArgsSchema, func=_runner)


def _wrap_extension_tools(ext: Dict[str, Any]):
    tools = []
    for fn in ext.get("tools", []):
        try:
            tools.append(_wrap_callable_as_tool(fn, ext.get("name", "unknown")))
        except Exception:
            continue
    return tools


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    return val if isinstance(val, str) and val.strip() else default


# ---- Models ----
class DomainResult(BaseModel):
    name: str
    output: Optional[str] = None
    duration_secs: Optional[float] = None
    llm_duration_secs: Optional[float] = None


class Timing(BaseModel):
    name: str
    seconds: float


class AgentResult(BaseModel):
    final: str
    results: List[DomainResult] = Field(default_factory=list)
    timings: List[Timing] = Field(default_factory=list)


# ---- Runtime caches ----
PRELOADED_EXTENSIONS: Optional[List[Dict[str, Any]]] = None
PRELOADED_SCHEMA: Optional[str] = None
LLM_DURATIONS: Dict[str, List[float]] = {}
BROADCAST_LLM: Dict[str, Optional[float]] = {"first_start": None, "last_end": None}
BROADCAST_LOCK = threading.Lock()
LLM_SPANS: Dict[str, List[Tuple[float, float]]] = {}
TOOL_CACHE: Dict[str, List[Any]] = {}
AGENT_CACHE: Dict[str, Any] = {}
OTHER_SCHEMA_CACHE: Dict[str, str] = {}
AUGMENTED_PROMPT_CACHE: Dict[str, str] = {}


def initialize_runtime() -> None:
    global PRELOADED_EXTENSIONS, PRELOADED_SCHEMA
    try:
        exts = discover_extensions()
    except Exception:
        exts = []
    PRELOADED_EXTENSIONS = exts
    parts: List[str] = []
    for ext in exts:
        parts.append(build_light_schema_for_extension(ext))
    PRELOADED_SCHEMA = "\n\n".join(p for p in parts if p)
    # Warm LLM client for domains
    try:
        get_chat_model(role="domain", model="gpt-4.1-mini", callbacks=[], temperature=0.0)
    except Exception:
        pass
    # Precompute caches: tools, other-domain schema, augmented prompts, and agents
    TOOL_CACHE.clear()
    OTHER_SCHEMA_CACHE.clear()
    AUGMENTED_PROMPT_CACHE.clear()
    AGENT_CACHE.clear()
    for ext in exts:
        name = ext.get("name", "unknown")
        # tools
        TOOL_CACHE[name] = _wrap_extension_tools(ext)
        # other domains' schema
        OTHER_SCHEMA_CACHE[name] = _build_other_domains_schema(name, exts)
        # augmented prompt
        AUGMENTED_PROMPT_CACHE[name] = _augmented_system_prompt(ext, exts)
    # Build agents last (depends on tools and prompts)
    try:
        from langgraph.prebuilt import create_react_agent
        for ext in exts:
            name = ext.get("name", "unknown")
            tools = TOOL_CACHE.get(name, [])
            prompt = _with_date_prefix(AUGMENTED_PROMPT_CACHE.get(name, ""))
            model = get_chat_model(role="domain", model="gpt-4.1-mini", callbacks=[], temperature=0.0)
            AGENT_CACHE[name] = create_react_agent(model, tools=tools, prompt=prompt)
    except Exception:
        # If agent warmup fails, runtime will lazy-build
        pass


def _get_extensions() -> List[Dict[str, Any]]:
    global PRELOADED_EXTENSIONS
    return PRELOADED_EXTENSIONS if PRELOADED_EXTENSIONS is not None else discover_extensions()


def _build_other_domains_schema(ext_name: str, all_exts: List[Dict[str, Any]]) -> str:
    sections: List[str] = []
    for ext in all_exts:
        if ext.get("name") == ext_name:
            continue
        sections.append(build_light_schema_for_extension(ext))
    return "\n\n".join([s for s in sections if s])


def _augmented_system_prompt(ext: Dict[str, Any], all_exts: List[Dict[str, Any]]) -> str:
    name = ext.get("name", "")
    base = ext.get("system_prompt", "").strip()
    other_schema = _build_other_domains_schema(name, all_exts)
    rules = (
        "Realtime-Fast Broadcast Mode: The same user message is sent to all domain agents concurrently.\n"
        "- Only respond if the request clearly pertains to your domain and tools. If not, reply with exactly: NULL\n"
        "- Do not take actions that belong to other domains.\n"
        "- Keep answers concise and domain-specific. Do not mention other agents or this system instruction.\n"
        "- When unsure, output NULL.\n\n"
        "Light Schema for other domains (context only):\n" + other_schema
    )
    return f"{base}\n\n{rules}" if base else rules


class LLMRunTracer(BaseCallbackHandler):
    def __init__(self, key: str):
        self.key = key
        self._starts: Dict[str, float] = {}

    def on_llm_start(self, serialized, prompts, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
        try:
            now = time.perf_counter()
            self._starts[str(run_id)] = now
            # update broadcast first_start
            with BROADCAST_LOCK:
                fs = BROADCAST_LLM.get("first_start")
                if fs is None or now < float(fs):
                    BROADCAST_LLM["first_start"] = now
                # initialize spans list for this key if needed
                if self.key not in LLM_SPANS:
                    LLM_SPANS[self.key] = []
        except Exception:
            pass

    def on_llm_end(self, response, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
        try:
            start = self._starts.pop(str(run_id), None)
            if isinstance(start, (int, float)):
                dur = time.perf_counter() - float(start)
                LLM_DURATIONS.setdefault(self.key, []).append(float(dur))
            # update broadcast last_end
            with BROADCAST_LOCK:
                end = time.perf_counter()
                BROADCAST_LLM["last_end"] = end
                try:
                    # record span
                    LLM_SPANS.setdefault(self.key, []).append((float(start) if isinstance(start, (int, float)) else end, float(end)))
                except Exception:
                    pass
        except Exception:
            pass


async def _run_domain_broadcast(ext: Dict[str, Any], user_prompt: str, chat_history: Optional[str], memory: Optional[str], all_exts: List[Dict[str, Any]]) -> DomainResult:
    from langchain_core.messages import SystemMessage, HumanMessage

    name = ext.get("name", "unknown")
    # reset per-domain LLM durations
    LLM_DURATIONS[f"domain:{name}"] = []
    tracer = LLMRunTracer(key=f"domain:{name}")
    # Get cached agent; if missing, build once and store
    agent = AGENT_CACHE.get(name)
    if agent is None:
        try:
            from langgraph.prebuilt import create_react_agent
            tools = TOOL_CACHE.get(name)
            if tools is None:
                tools = _wrap_extension_tools(ext)
                TOOL_CACHE[name] = tools
            prompt_text = AUGMENTED_PROMPT_CACHE.get(name)
            if prompt_text is None:
                prompt_text = _augmented_system_prompt(ext, all_exts)
                AUGMENTED_PROMPT_CACHE[name] = prompt_text
            model = get_chat_model(role="domain", model="gpt-4.1-mini", callbacks=[tracer], temperature=0.0)
            agent = create_react_agent(model, tools=tools, prompt=_with_date_prefix(prompt_text))
            AGENT_CACHE[name] = agent
        except Exception as e:
            return DomainResult(name=name, output=f"Error building agent: {str(e)}")

    messages: List[Any] = [SystemMessage(content=_with_date_prefix("You are a domain sub-agent."))]
    if chat_history or memory:
        messages.append(SystemMessage(content=(
            "Conversation context to consider when responding.\n"
            + (f"Chat history:\n{chat_history}\n\n" if chat_history else "")
            + (f"Memory:\n{memory}" if memory else "")
        )))
    messages.append(HumanMessage(content=user_prompt))

    t0 = time.perf_counter()
    try:
        result = await agent.ainvoke({"messages": messages}, config={"recursion_limit": 8, "callbacks": [tracer]})
        dur = time.perf_counter() - t0
        # result is {"messages": [...]} ; take last message content
        m = result.get("messages") if isinstance(result, dict) else None
        content: Optional[str] = None
        if isinstance(m, list) and m:
            last = m[-1]
            content = getattr(last, "content", None)
        if not isinstance(content, str):
            content = str(result)
        llm_secs = float(sum(LLM_DURATIONS.get(f"domain:{name}", []) or [0.0]))
        return DomainResult(name=name, output=(content or "").strip(), duration_secs=float(dur), llm_duration_secs=llm_secs)
    except Exception as e:
        llm_secs = float(sum(LLM_DURATIONS.get(f"domain:{name}", []) or [0.0]))
        return DomainResult(name=name, output=f"Error: {str(e)}", duration_secs=None, llm_duration_secs=llm_secs)


def _run_domain_broadcast_sync(ext: Dict[str, Any], user_prompt: str, chat_history: Optional[str], memory: Optional[str], all_exts: List[Dict[str, Any]]) -> DomainResult:
    """Synchronous version for threaded execution."""
    from langchain_core.messages import SystemMessage, HumanMessage

    name = ext.get("name", "unknown")
    # reset per-domain LLM durations
    LLM_DURATIONS[f"domain:{name}"] = []
    tracer = LLMRunTracer(key=f"domain:{name}")
    # Get cached agent; if missing, build once and store
    agent = AGENT_CACHE.get(name)
    if agent is None:
        try:
            from langgraph.prebuilt import create_react_agent
            tools = TOOL_CACHE.get(name)
            if tools is None:
                tools = _wrap_extension_tools(ext)
                TOOL_CACHE[name] = tools
            prompt_text = AUGMENTED_PROMPT_CACHE.get(name)
            if prompt_text is None:
                prompt_text = _augmented_system_prompt(ext, all_exts)
                AUGMENTED_PROMPT_CACHE[name] = prompt_text
            model = get_chat_model(role="domain", model="gpt-4.1-mini", callbacks=[tracer], temperature=0.0)
            agent = create_react_agent(model, tools=tools, prompt=_with_date_prefix(prompt_text))
            AGENT_CACHE[name] = agent
        except Exception as e:
            return DomainResult(name=name, output=f"Error building agent: {str(e)}")

    messages: List[Any] = []
    if chat_history or memory:
        messages.append(SystemMessage(content=(
            "Conversation context to consider when responding.\n"
            + (f"Chat history:\n{chat_history}\n\n" if chat_history else "")
            + (f"Memory:\n{memory}" if memory else "")
        )))
    messages.append(HumanMessage(content=user_prompt))

    t0 = time.perf_counter()
    try:
        result = agent.invoke({"messages": messages}, config={"recursion_limit": 8, "callbacks": [tracer]})
        dur = time.perf_counter() - t0
        # result is {"messages": [...]} ; take last message content
        m = result.get("messages") if isinstance(result, dict) else None
        content: Optional[str] = None
        if isinstance(m, list) and m:
            last = m[-1]
            content = getattr(last, "content", None)
        if not isinstance(content, str):
            content = str(result)
        llm_secs = float(sum(LLM_DURATIONS.get(f"domain:{name}", []) or [0.0]))
        return DomainResult(name=name, output=(content or "").strip(), duration_secs=float(dur), llm_duration_secs=llm_secs)
    except Exception as e:
        llm_secs = float(sum(LLM_DURATIONS.get(f"domain:{name}", []) or [0.0]))
        return DomainResult(name=name, output=f"Error: {str(e)}", duration_secs=None, llm_duration_secs=llm_secs)


async def run_agent(user_prompt: str, chat_history: Optional[str] = None, memory: Optional[str] = None) -> AgentResult:
    # Get all extensions
    exts = _get_extensions()
    # Optional filter: restrict to specific domain names via env (comma-separated)
    only = _get_env("RFAST_ONLY_DOMAINS")
    if isinstance(only, str) and only.strip():
        wanted = {n.strip() for n in only.split(",") if n.strip()}
        exts = [e for e in exts if e.get("name") in wanted]
    if not exts:
        return AgentResult(final="No extensions discovered. Ensure files matching *_tool.py exist under extensions.", results=[], timings=[])

    # Reset broadcast LLM span tracking for this run
    with BROADCAST_LOCK:
        BROADCAST_LLM["first_start"] = None
        BROADCAST_LLM["last_end"] = None
        LLM_SPANS.clear()

    # Execution mode: threads or asyncio (default)
    exec_mode = (_get_env("RFAST_EXECUTION", "async") or "async").lower()
    t0 = time.perf_counter()
    results: List[DomainResult] = []
    if exec_mode == "threads":
        from concurrent.futures import ThreadPoolExecutor, as_completed
        max_workers = int(_get_env("RFAST_MAX_WORKERS", str(min(8, max(1, len(exts))))) or 4)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {}
            for ext in exts:
                future = pool.submit(_run_domain_broadcast_sync, ext, user_prompt, chat_history, memory, exts)
                future_map[future] = ext
            for fut in as_completed(future_map):
                try:
                    results.append(fut.result())
                except Exception as e:
                    name = future_map[fut].get("name", "unknown")
                    results.append(DomainResult(name=name, output=f"Error: {str(e)}"))
    else:
        # Asyncio path
        tasks = [
            asyncio.create_task(_run_domain_broadcast(ext, user_prompt, chat_history, memory, exts)) for ext in exts
        ]
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=float(_get_env("DOMAIN_TIMEOUT_SECS", "60") or 60))
        except asyncio.TimeoutError:
            # include completed ones; mark timeouts as NULL-equivalent (no output)
            for idx, task in enumerate(tasks):
                name = exts[idx].get("name", f"ext{idx}")
                if not task.done():
                    continue
                if not task.cancelled():
                    try:
                        results.append(task.result())
                    except Exception as e:
                        results.append(DomainResult(name=name, output=f"Error: {str(e)}"))

    # Build final combined output: only domains with non-NULL, non-empty outputs
    responders: List[DomainResult] = []
    for dr in results:
        out = (dr.output or "").strip()
        if not out:
            continue
        if out.upper() == "NULL":
            continue
        responders.append(dr)

    lines: List[str] = []
    if responders:
        for dr in responders:
            lines.append(f"[{dr.name}]\n{dr.output}")
        final = "\n\n".join(lines)
    else:
        final = "No domain produced a response (all returned NULL)."

    elapsed = time.perf_counter() - t0
    timings: List[Timing] = [Timing(name="broadcast", seconds=float(elapsed))]
    # Include per-domain LLM times
    for dr in results:
        if isinstance(dr.llm_duration_secs, (int, float)):
            timings.append(Timing(name=f"llm:{dr.name}", seconds=float(dr.llm_duration_secs)))
    # Broadcast LLM span and per-domain start/end offsets
    fs = BROADCAST_LLM.get("first_start")
    le = BROADCAST_LLM.get("last_end")
    if isinstance(fs, (int, float)) and isinstance(le, (int, float)) and le >= fs:
        total_llm_span = float(le - fs)
        timings.append(Timing(name="broadcast_llm_span", seconds=total_llm_span))
        # collect end offsets, then print in ascending order
        end_offsets: List[Tuple[str, float]] = []
        for dr in results:
            key = f"domain:{dr.name}"
            spans = LLM_SPANS.get(key) or []
            if spans:
                latest = max(e for _, e in spans)
                end_offsets.append((dr.name, float(latest - fs)))
        for name, off in sorted(end_offsets, key=lambda x: x[1]):
            timings.append(Timing(name=f"llm_end:{name}", seconds=off))
    return AgentResult(final=final, results=results, timings=timings)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Realtime-Fast Agent (broadcast to all domains)")
    parser.add_argument("-p", "--prompt", type=str, default="turn on swtitch.living_room_light", help="Test prompt")
    args = parser.parse_args(argv)

    # Preload
    try:
        initialize_runtime()
    except Exception:
        pass

    try:
        ret = asyncio.run(run_agent(args.prompt))
    except RuntimeError:
        # Create a new loop explicitly if none exists
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            ret = loop.run_until_complete(run_agent(args.prompt))
        finally:
            try:
                loop.close()
            except Exception:
                pass

    if isinstance(ret, AgentResult):
        # Minimal console report
        results = ret.results or []
        if results:
            print("Responders:")
            for dr in results:
                out = (dr.output or "").strip()
                flag = "OK" if out and out.upper() != "NULL" else "NULL"
                print(f"- {dr.name}: {flag}")
            print("")
        print(ret.final)
        if ret.timings:
            print("\nTimings:")
            for tm in ret.timings:
                print(f"- {tm.name}: {tm.seconds:.2f}s")
    else:
        print(str(ret))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

 