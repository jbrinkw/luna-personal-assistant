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
    """Load the root project page and the project notes page into working memory.
    Example Prompt: Load the root page and notes for project Luna.
    Example Args: {"project_id": "Luna", "include_children": false}
    Returns both the root page text and the notes page text. Only includes child projects when include_children=true.
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

        def _read_root_and_notes_for(proj) -> Tuple[Optional[str], Optional[str], str, Optional[str]]:
            root_path = str(getattr(proj, "file_path", ""))
            try:
                root_text = Path(root_path).read_text(encoding="utf-8") if root_path and Path(root_path).exists() else None
            except Exception:
                root_text = None
            # Prefer explicit linked note_file; else prefer sibling Notes.md if it exists
            note_path_obj: Optional[Path] = None
            nfile = getattr(proj, "note_file", None)
            if nfile and Path(nfile).exists():
                note_path_obj = Path(nfile)
            else:
                candidate = Path(root_path).parent / "Notes.md" if root_path else None
                if candidate and candidate.exists():
                    note_path_obj = candidate
            note_path = str(note_path_obj) if isinstance(note_path_obj, Path) else None
            try:
                note_text = note_path_obj.read_text(encoding="utf-8") if note_path_obj else None
            except Exception:
                note_text = None
            return root_text, note_text, root_path, note_path

        parts: List[str] = []
        root_text, note_text, root_path, note_path = _read_root_and_notes_for(target)
        parts.append(f"[Root Project Page] ({root_path})\n" + (root_text if isinstance(root_text, str) and root_text.strip() else "<no root page content>"))
        parts.append(f"\n[Project Notes Page] ({note_path or '<none>'})\n" + (note_text if isinstance(note_text, str) and note_text.strip() else "<no notes page content>"))

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
                c_root, c_note, c_root_path, c_note_path = _read_root_and_notes_for(child)
                parts.append("\n\n---\n" + f"[Child Project: {getattr(child, 'project_id', cid)}]\n")
                parts.append(f"[Root Page] ({c_root_path})\n" + (c_root if isinstance(c_root, str) and c_root.strip() else "<no root page content>"))
                parts.append(f"\n[Notes Page] ({c_note_path or '<none>'})\n" + (c_note if isinstance(c_note, str) and c_note.strip() else "<no notes page content>"))
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

    # Helper to build dynamic Todoist structure for docstrings
    def _build_todoist_structure_bulleted_list() -> str:
        try:
            from extensions.todo_list import todo_list_tool as tlt  # type: ignore
            proj_resp = tlt.TODOLIST_GET_list_projects()
            # proj_resp may be a Pydantic model or error wrapper
            projects = []
            try:
                data = proj_resp.model_dump() if hasattr(proj_resp, "model_dump") else json.loads(str(proj_resp))
            except Exception:
                data = None
            if isinstance(data, dict) and data.get("success") and isinstance(data.get("projects"), list):
                projects = data.get("projects")
            lines: List[str] = []
            for p in projects:
                pid = p.get("id")
                pname = p.get("name")
                lines.append(f"- {pname} (id: {pid})")
                try:
                    secs_resp = tlt.TODOLIST_GET_list_sections(project_id=int(pid))
                    sdata = secs_resp.model_dump() if hasattr(secs_resp, "model_dump") else json.loads(str(secs_resp))
                except Exception:
                    sdata = None
                if isinstance(sdata, dict) and sdata.get("success") and isinstance(sdata.get("sections"), list):
                    for s in sdata.get("sections"):
                        sname = s.get("name")
                        sid = s.get("id")
                        lines.append(f"  - [section] {sname} (id: {sid})")
            return "\n".join(lines) if lines else "<no Todoist projects found or token missing>"
        except Exception:
            return "<todo list structure unavailable>"

    # Embedded push tool: commit approved summaries and action items
    def PROJECT_SYNC_push_updates(updates_json: str, notes_section: Optional[str] = "Summary", default_due_string: Optional[str] = None) -> str:
        """Push approved summaries and action items to Notes and Todoist.
        Example Prompt: Push the approved summary and tasks now.
        Example Args: {"updates_json": "{\"projects\":[{\"project_id\":\"Luna\",\"summary\":\"...\",\"action_items\":[\"...\"]}]}"}
        Behavior:
        - Appends the "summary" verbatim to today's Notes.md for each project under the specified notes_section (default: "Summary").
        - Creates each "action_items" entry verbatim as a Todoist task under a project matched by name (case-insensitive). If no match, falls back to Inbox.
        """
        results: List[Dict[str, Any]] = []
        errors: List[str] = []
        # Parse payload
        try:
            payload = json.loads(updates_json)
        except Exception as e:
            return json.dumps({"success": False, "message": f"invalid updates_json: {e}"})
        items = payload.get("projects") if isinstance(payload, dict) else None
        if not isinstance(items, list) or not items:
            return json.dumps({"success": False, "message": "no projects provided"})

        # Build Todoist project name -> id map once
        todo_name_to_id: Dict[str, int] = {}
        try:
            from extensions.todo_list import todo_list_tool as tlt  # type: ignore
            proj_resp = tlt.TODOLIST_GET_list_projects()
            pdata = proj_resp.model_dump() if hasattr(proj_resp, "model_dump") else json.loads(str(proj_resp))
            if isinstance(pdata, dict) and pdata.get("success"):
                for p in pdata.get("projects") or []:
                    try:
                        nm = str(p.get("name") or "").strip()
                        pid = int(p.get("id")) if p.get("id") is not None else None
                        if nm and isinstance(pid, int):
                            todo_name_to_id[nm.lower()] = pid
                    except Exception:
                        continue
        except Exception as e:
            errors.append(f"todoist project list error: {e}")

        # Process per project
        from extensions.notes import notes_tool as nt  # type: ignore
        try:
            from extensions.todo_list import todo_list_tool as tlt  # type: ignore
        except Exception as e:
            return json.dumps({"success": False, "message": f"todo list module import error: {e}"})

        created_total = 0
        for entry in items:
            proj_id = str(entry.get("project_id") or "").strip() if isinstance(entry, dict) else ""
            summary = str(entry.get("summary") or "").strip() if isinstance(entry, dict) else ""
            actions = entry.get("action_items") if isinstance(entry, dict) else None
            if not proj_id:
                results.append({"project_id": proj_id, "notes_updated": False, "todos_created": 0, "errors": ["missing project_id"]})
                continue
            errs: List[str] = []
            notes_ok = False
            todos_created = 0

            # Update notes
            if summary:
                try:
                    resp = nt.NOTES_UPDATE_project_note(project_id=proj_id, content=summary, section_id=(notes_section or "Summary"))
                    # no need to inspect response deeply for now
                    notes_ok = True
                except Exception as e:
                    errs.append(f"notes error: {e}")
            else:
                # still succeed if only todos
                notes_ok = True

            # Create todos
            if isinstance(actions, list):
                # Resolve target Todoist project by name
                target_pid: Optional[int] = None
                if todo_name_to_id:
                    target_pid = todo_name_to_id.get(proj_id.lower())
                for task_text in actions:
                    try:
                        content = str(task_text)
                        if not content.strip():
                            continue
                        payload: Dict[str, Any] = {"content": content, "project_id": int(target_pid) if isinstance(target_pid, int) else int(todo_name_to_id.get("inbox", 0) or 0)}
                        if default_due_string and default_due_string.strip():
                            payload["due_string"] = default_due_string.strip()
                        tlt.TODOLIST_ACTION_create_task(**payload)
                        todos_created += 1
                    except Exception as e:
                        errs.append(f"todo error: {e}")

            created_total += todos_created
            results.append({"project_id": proj_id, "notes_updated": notes_ok, "todos_created": todos_created, "errors": errs})

        return json.dumps({"success": True, "projects": results, "total_todos_created": created_total, "errors": errors})

    # Attach dynamic docstring to push tool including current Todoist structure
    try:
        todo_structure = _build_todoist_structure_bulleted_list()
        PROJECT_SYNC_push_updates.__doc__ = (
            "Push approved summaries and action items to Notes and Todoist.\n\n"
            "Input JSON shape (pass as updates_json):\n"
            "{\n  \"projects\": [\n    {\n      \"project_id\": \"string\",\n      \"summary\": \"string\",\n      \"action_items\": [\"string\", \"string\"]\n    }\n  ]\n}\n\n"
            "Behavior:\n"
            "- Appends \"summary\" verbatim to today's Notes.md under section \"Summary\".\n"
            "- Creates each action item verbatim as a Todoist task in a project matched by name (case-insensitive).\n"
            "- If no match, tasks go to Inbox.\n\n"
            "Current Todoist projects and sections:\n" + (todo_structure or "<unavailable>")
        )
    except Exception:
        pass

    # Register push tool
    try:
        tools.append(_wrap_callable_as_tool(PROJECT_SYNC_push_updates, "Project Sync"))
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
        core_instructions = (
            "You are a focused project assistant.\n"
            "- When the user references a project, call PROJECT_NOTES_GET_load first to load the root page and the notes page.\n"
            "- Only pass include_children=true if the user explicitly requests child projects.\n"
            "- Use Todo List tools for task operations.\n"
            "- Use web search only when external info is needed.\n"
            "\n"
            "Summarization workflow (no tools until push):\n"
            "- Do NOT produce any draft summary unless the user explicitly asks (e.g., \"summarize\").\n"
            "- When asked to summarize, respond in natural language: for each project, provide a concise multi-paragraph summary and a bulleted list of action items. Do NOT include JSON or code fences. End by asking for approval or edits.\n"
            "- Only when the user asks to \"format for upload\", \"show upload JSON\", or \"prepare to push\", convert the approved draft into JSON EXACTLY in this shape (no prose, no code fences, no extra keys):\n"
            "{\n  \"projects\": [\n    {\n      \"project_id\": \"string\",\n      \"summary\": \"concise multi-paragraph summary\",\n      \"action_items\": [\"action 1\", \"action 2\"]\n    }\n  ]\n}\n"
            "- Do not call any tools during drafting.\n"
            "\n"
            "Push workflow:\n"
            "- Only after the user asks to push/upload/apply, call PROJECT_SYNC_push_updates with the approved JSON verbatim.\n"
            "- The tool will append summaries to Notes and create Todoist tasks.\n"
        )
        if hierarchy and hierarchy.strip():
            final_prompt = (
                "Project hierarchy (use project_id in parentheses when calling tools):\n" + hierarchy + "\n\n" + core_instructions
            )
        else:
            final_prompt = core_instructions
        agent = create_react_agent(model, tools=tools, prompt=final_prompt)
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
        # Keep streaming prompt consistent and with hierarchy first
        hierarchy = _build_project_hierarchy_bulleted_list()
        core_instructions = (
            "You are a focused project assistant.\n"
            "- When the user references a project, call PROJECT_NOTES_GET_load first to load the root page and the notes page.\n"
            "- Only pass include_children=true if the user explicitly requests child projects.\n"
            "- Use Todo List tools for task operations.\n"
            "- Use web search only when external info is needed.\n"
            "\n"
            "Summarization workflow (no tools until push):\n"
            "- Do NOT produce any draft summary unless the user explicitly asks to \"summarize\".\n"
            "- When asked to summarize, respond with JSON ONLY in exactly this shape (no prose, no code fences, no extra keys):\n"
            "{\n  \"projects\": [\n    {\n      \"project_id\": \"string\",\n      \"summary\": \"concise multi-paragraph summary\",\n      \"action_items\": [\"action 1\", \"action 2\"]\n    }\n  ]\n}\n"
            "- Do not call any tools during drafting.\n"
            "- Iterate with the user using JSON-only responses until they confirm the draft is approved.\n"
            "\n"
            "Push workflow:\n"
            "- When the user asks to push/upload/apply, call PROJECT_SYNC_push_updates with the approved JSON verbatim.\n"
            "- The tool will append summaries to Notes and create Todoist tasks.\n"
        )
        if hierarchy and hierarchy.strip():
            final_prompt = (
                "Project hierarchy (use project_id in parentheses when calling tools):\n" + hierarchy + "\n\n" + core_instructions
            )
        else:
            final_prompt = core_instructions
        agent = create_react_agent(model, tools=tools, prompt=final_prompt)
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



