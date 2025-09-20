import os
import sys
import json
import time
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, get_type_hints, Callable

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


def _wrap_callable_as_tool(fn: Callable[..., Any], ext_name: str):
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


def _active_models() -> Dict[str, str]:
    # Minimal stub to keep server banners happy
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


# ---- Embedded Project Notes tool ----
def _vault_base_dir() -> Path:
    # Allow override via env; default to repo path
    custom = os.getenv("NOTES_VAULT_DIR")
    if custom and custom.strip():
        return Path(custom).expanduser().resolve()
    return Path(PROJECT_ROOT) / "extensions" / "notes" / "Obsidian Vault"


def PROJECT_NOTES_GET_load(project_id: str, include_children: bool = False) -> str:
    """Load the note file for a project into working memory.
    Example Prompt: Load the notes for project Luna.
    Example Args: {"project_id": "Luna", "include_children": false}
    Returns the note text for the project. Only includes child projects when include_children=true.
    """
    try:
        base_dir = _vault_base_dir()
        if not base_dir.exists():
            return f"Error: Base directory not found: {base_dir}"

        # Import utilities locally to avoid hard import errors at module import time
        from extensions.notes import project_hierarchy as ph  # type: ignore

        projects = ph.build_projects(base_dir)
        ph.link_notes(base_dir, projects)

        if not isinstance(project_id, str) or not project_id.strip():
            return "Error: project_id is required"
        pid = project_id.strip()

        target = projects.get(pid)
        if target is None:
            # Fallback: case-insensitive match on project_id keys
            lookup = {k.lower(): k for k in projects.keys()}
            real = lookup.get(pid.lower())
            if real:
                target = projects.get(real)
        if target is None:
            return f"Error: project not found: {pid}"

        def _read_note_for(proj) -> Optional[str]:
            try:
                note_path: Optional[Path] = proj.note_file if getattr(proj, "note_file", None) else proj.file_path
                if note_path and Path(note_path).exists():
                    return Path(note_path).read_text(encoding="utf-8")
            except Exception:
                return None
            return None

        parts: List[str] = []
        main_text = _read_note_for(target)
        if isinstance(main_text, str) and main_text.strip():
            parts.append(main_text)
        else:
            parts.append(f"<no note content available for project {pid}>")

        if include_children:
            # Breadth-first traversal of children
            queue: List[str] = list(getattr(target, "children", []) or [])
            seen: set[str] = set()
            while queue:
                cid = queue.pop(0)
                if cid in seen:
                    continue
                seen.add(cid)
                child = projects.get(cid)
                if not child:
                    continue
                ctext = _read_note_for(child)
                header = f"\n\n---\n[Child Project: {getattr(child, 'project_id', cid)}]\n"
                parts.append(header + (ctext if isinstance(ctext, str) and ctext.strip() else "<no note content>"))
                # enqueue grandchildren
                queue.extend(list(getattr(child, "children", []) or []))

        # Optionally truncate extreme lengths
        max_chars = int(os.getenv("PROJECT_NOTES_MAX_CHARS", "250000") or 250000)
        out = "\n\n".join(parts)
        if len(out) > max_chars:
            return out[:max_chars] + "\n\n<content truncated>"
        return out
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"


def _build_project_hierarchy_bulleted_list() -> str:
    """Return a simple nested bulleted list of projects (name and id).
    Example line: "- Luna (id: Luna)"
    Children are indented by two spaces per level.
    """
    try:
        base_dir = _vault_base_dir()
        if not base_dir.exists():
            return "<project hierarchy unavailable: vault not found>"
        from extensions.notes import project_hierarchy as ph  # type: ignore
        projects = ph.build_projects(base_dir)
        if not projects:
            return "<no projects found>"
        ph.link_notes(base_dir, projects)

        lines: List[str] = []

        def recurse(pid: str, level: int) -> None:
            proj = projects[pid]
            indent = "  " * level
            name = getattr(proj, "display_name", pid)
            proj_id = getattr(proj, "project_id", pid)
            lines.append(f"{indent}- {name} (id: {proj_id})")
            for cid in getattr(proj, "children", []) or []:
                if cid in projects:
                    recurse(cid, level + 1)

        for root_id in ph.roots_of(projects):
            recurse(root_id, 0)
        return "\n".join(lines)
    except Exception:
        return "<project hierarchy unavailable>"


def _build_tools() -> List[Any]:
    tools: List[Any] = []

    # Embedded notes loader
    try:
        tools.append(_wrap_callable_as_tool(PROJECT_NOTES_GET_load, "Project Notes"))
    except Exception:
        pass

    # Todo List: include all exposed tools from the extension module
    try:
        from extensions.todo_list import todo_list_tool as tlt  # type: ignore
        for fn in getattr(tlt, "TOOLS", []) or []:
            if callable(fn):
                try:
                    tools.append(_wrap_callable_as_tool(fn, getattr(tlt, "NAME", "Todo List")))
                except Exception:
                    continue
    except Exception:
        pass

    # GeneralByte: include ONLY web search
    try:
        from extensions.generalbyte import generalbyte_tool as gbt  # type: ignore
        web_fn = getattr(gbt, "GENERAL_GET_web_search", None)
        if callable(web_fn):
            try:
                tools.append(_wrap_callable_as_tool(web_fn, getattr(gbt, "NAME", "GeneralByte")))
            except Exception:
                pass
    except Exception:
        pass

    return tools


def initialize_runtime(tool_root: Optional[str] = None) -> None:
    global PRELOADED_TOOLS
    PRELOADED_TOOLS = _build_tools()


async def run_agent(user_prompt: str, chat_history: Optional[str] = None, memory: Optional[str] = None, tool_root: Optional[str] = None) -> AgentResult:
    # Discover/warm tools (no external discovery; we assemble a filtered set)
    if not PRELOADED_TOOLS:
        initialize_runtime()
    tools = PRELOADED_TOOLS or []
    if not tools:
        msg = "No tools available. Ensure dependencies are installed and modules import."
        return AgentResult(final=msg, results=[], timings=[], content=msg, response_time_secs=0.0, traces=[])

    # Build a ReAct agent with our filtered tools
    try:
        from langgraph.prebuilt import create_react_agent
        model = get_chat_model(role="domain", model=_get_env("REACT_MODEL", "gpt-4.1"), callbacks=[LLMRunTracer("react")], temperature=0.0)
        # Clear traces for this run
        del RUN_TRACES[:]
        hierarchy = _build_project_hierarchy_bulleted_list()
        agent_instructions = (
            "You are a focused project assistant.\n"
            "- When the user references a project, call PROJECT_NOTES_GET_load first to load context.\n"
            "- Only pass include_children=true if the user explicitly requests child projects.\n"
            "- Use Todo List tools for task operations.\n"
            "- Use web search only when external info is needed.\n"
        )
        if hierarchy and hierarchy.strip():
            agent_instructions += ("\n\nProject hierarchy (use project_id in parentheses when calling tools):\n" + hierarchy)
        agent = create_react_agent(model, tools=tools, prompt=agent_instructions)
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

    # Invoke agent
    import asyncio
    t0 = time.perf_counter()
    try:
        result = await agent.ainvoke({"messages": messages}, config={"recursion_limit": 8, "callbacks": [LLMRunTracer("react")]})
    except RuntimeError:
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


async def run_agent_stream(user_prompt: str, chat_history: Optional[str] = None, memory: Optional[str] = None, tool_root: Optional[str] = None):
    """Yield incremental text chunks while the agent generates a response.

    Fallback: if streaming is unavailable, yields the final response once.
    """
    # Ensure tools initialized
    if not PRELOADED_TOOLS:
        initialize_runtime()
    tools = PRELOADED_TOOLS or []
    if not tools:
        yield "No tools available. Ensure dependencies are installed and modules import."
        return

    # Build agent (same config as run_agent)
    try:
        from langgraph.prebuilt import create_react_agent
        model = get_chat_model(role="domain", model=_get_env("REACT_MODEL", "gpt-4.1"), callbacks=[LLMRunTracer("react")], temperature=0.0)
        agent_instructions = (
            "You are a focused project assistant.\n"
            "- When the user references a project, call PROJECT_NOTES_GET_load first to load context.\n"
            "- Only pass include_children=true if the user explicitly requests child projects.\n"
            "- Use Todo List tools for task operations.\n"
            "- Use web search only when external info is needed.\n"
        )
        agent = create_react_agent(model, tools=tools, prompt=agent_instructions)
    except Exception:
        # If building agent fails, just yield non-streaming result from run_agent
        res = await run_agent(user_prompt, chat_history=chat_history, memory=memory, tool_root=tool_root)
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

    yielded_any = False
    try:
        # Prefer event-streaming for token deltas
        async for event in agent.astream_events({"messages": messages}, config={"recursion_limit": 8, "callbacks": [LLMRunTracer("react")]}, version="v1"):
            try:
                ev = event.get("event") if isinstance(event, dict) else getattr(event, "event", None)
                if ev == "on_chat_model_stream":
                    data = event.get("data") if isinstance(event, dict) else getattr(event, "data", {})
                    chunk = (data or {}).get("chunk") if isinstance(data, dict) else getattr(data, "chunk", None)
                    text = getattr(chunk, "content", None)
                    if isinstance(text, str) and text:
                        yielded_any = True
                        yield text
            except Exception:
                # Ignore malformed events; continue streaming
                continue
    except Exception:
        # If streaming path fails, fall back to single-shot
        pass

    if not yielded_any:
        # Fallback to non-streaming execution
        res = await run_agent(user_prompt, chat_history=chat_history, memory=memory, tool_root=tool_root)
        yield res.final
        return


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Project Agent (embedded notes tool + filtered tools)")
    parser.add_argument("-p", "--prompt", type=str, default="what can you do?", help="Test prompt")
    args = parser.parse_args(argv)
    try:
        import asyncio
        ret = asyncio.run(run_agent(args.prompt))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        ret = loop.run_until_complete(run_agent(args.prompt))
    print(ret.final)
    if ret.traces:
        print("\nTools used (in order):")
        for t in ret.traces:
            try:
                args_str = json.dumps(t.args, ensure_ascii=False)
            except Exception:
                args_str = str(t.args)
            # Limit extremely long outputs for readability
            out = t.output if isinstance(t.output, str) else str(t.output)
            max_show = int(os.getenv("CLI_TOOL_OUTPUT_MAX_CHARS", "4000") or 4000)
            if len(out) > max_show:
                out = out[:max_show] + "\n<output truncated>"
            print(f"- {t.tool}")
            print(f"  args: {args_str}")
            print(f"  output:\n{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


