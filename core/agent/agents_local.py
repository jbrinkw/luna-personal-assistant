import os
import time
import json
from typing import Any, Dict, Optional, Tuple, List

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler


def _require_openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set.")
    return key


def make_llm(model_name: str) -> ChatOpenAI:
    _require_openai_key()
    return ChatOpenAI(model=model_name, temperature=0)


class ToolLogCallback(BaseCallbackHandler):
    """Capture tool name, args, result and duration for each tool call."""

    def __init__(self) -> None:
        self._starts: Dict[Any, tuple[float, str, Any]] = {}
        self.tool_calls: List[Dict[str, Any]] = []

    def on_tool_start(self, serialized, input_str, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
        try:
            name = None
            if isinstance(serialized, dict):
                name = serialized.get("name") or serialized.get("id")
            if not name:
                name = str(serialized)
        except Exception:
            name = "<unknown_tool>"

        parsed_args: Any = input_str
        if isinstance(input_str, str):
            try:
                parsed_args = json.loads(input_str)
            except Exception:
                parsed_args = input_str
        self._starts[run_id] = (time.perf_counter(), str(name), parsed_args)

    def on_tool_end(self, output, run_id, **kwargs):  # type: ignore[override]
        start, name, args = self._starts.pop(run_id, (None, None, None))
        if start is None:
            return
        result: Any = output
        if isinstance(output, str):
            try:
                result = json.loads(output)
            except Exception:
                result = output
        self.tool_calls.append(
            {
                "name": name,
                "args": args,
                "result": result,
                "duration_s": round(time.perf_counter() - start, 3),
            }
        )

    def on_tool_error(self, error, run_id, **kwargs):  # type: ignore[override]
        start, name, args = self._starts.pop(run_id, (None, None, None))
        if start is None:
            return
        self.tool_calls.append(
            {
                "name": name,
                "args": args,
                "error": str(error),
                "duration_s": round(time.perf_counter() - start, 3),
            }
        )


def build_general_agent(model_name: str = "gpt-4.1"):
    # Import local tools lazily to avoid import-time side effects
    from extensions.generalbyte.code import tool_local as gb

    tools = []
    for name in dir(gb):
        if not name.startswith("GENERAL_"):
            continue
        obj = getattr(gb, name)
        if callable(obj):
            tools.append(obj)
    return create_react_agent(make_llm(model_name), tools)


def build_homeassistant_agent(model_name: str = "gpt-4.1"):
    from core.integrations import homeassistant_local_tools as ha

    tools = []
    for name in dir(ha):
        if not name.startswith("HA_"):
            continue
        obj = getattr(ha, name)
        if callable(obj):
            tools.append(obj)
    return create_react_agent(make_llm(model_name), tools)


def build_chefbyte_agent(model_name: str = "gpt-4.1"):
    from extensions.chefbyte.code import local_tools as chef

    tools = []
    for name in dir(chef):
        if not name.startswith("CHEF_"):
            continue
        obj = getattr(chef, name)
        if callable(obj):
            tools.append(obj)
    return create_react_agent(make_llm(model_name), tools)


def build_coachbyte_agent(model_name: str = "gpt-4.1"):
    # Ensure repository root is on sys.path for absolute imports during runtime
    try:
        from extensions.coachbyte.ui import tools as coach_ui
    except ModuleNotFoundError:
        import sys as _sys
        import os as _os
        _sys.path.insert(0, _os.path.abspath(os.path.join(_os.path.dirname(__file__), '..', '..')))
        from extensions.coachbyte.ui import tools as coach_ui  # type: ignore

    tools = []
    exported = getattr(coach_ui, "__all__", None)
    if isinstance(exported, (list, tuple)):
        names = [n for n in exported if isinstance(n, str)]
    else:
        names = [n for n in dir(coach_ui) if not n.startswith("_")]

    for name in names:
        obj = getattr(coach_ui, name, None)
        if callable(obj):
            tools.append(obj)
    return create_react_agent(make_llm(model_name), tools)


async def run_general(user_input: str, model_name: str = "gpt-4.1") -> Tuple[Optional[str], float, List[Dict[str, Any]]]:
    agent = build_general_agent(model_name)
    system = SystemMessage(
        content=(
            "You are the GeneralByte domain agent. Use tools when needed and return a concise answer."
        )
    )
    t0 = time.perf_counter()
    cb = ToolLogCallback()
    resp = await agent.ainvoke({"messages": [system, HumanMessage(content=user_input)]}, config={"callbacks": [cb]})
    dt = round(time.perf_counter() - t0, 3)
    messages = resp.get("messages") if isinstance(resp, dict) else None
    final_msg = messages[-1].content if messages else None
    return (str(final_msg) if final_msg is not None else None), dt, cb.tool_calls


async def run_homeassistant(user_input: str, model_name: str = "gpt-4.1") -> Tuple[Optional[str], float, List[Dict[str, Any]]]:
    agent = build_homeassistant_agent(model_name)
    system = SystemMessage(
        content=(
            "You are the HomeAssistant domain agent. Use tools for device control/status and return a concise answer.\n"
            "Device tools accept either a friendly name or an entity_id. If you are not certain of the entity_id, DO NOT INVENT one.\n"
            "Instead, pass the exact friendly name (e.g., 'Living Room Fan'), or call HA_GET_devices to list devices and select the exact name.\n"
            "If multiple devices match a name, ask the user to clarify rather than guessing."
        )
    )
    t0 = time.perf_counter()
    cb = ToolLogCallback()
    resp = await agent.ainvoke({"messages": [system, HumanMessage(content=user_input)]}, config={"callbacks": [cb]})
    dt = round(time.perf_counter() - t0, 3)
    messages = resp.get("messages") if isinstance(resp, dict) else None
    final_msg = messages[-1].content if messages else None
    return (str(final_msg) if final_msg is not None else None), dt, cb.tool_calls


async def run_chefbyte(user_input: str, model_name: str = "gpt-4.1") -> Tuple[Optional[str], float, List[Dict[str, Any]]]:
    agent = build_chefbyte_agent(model_name)
    system = SystemMessage(
        content=(
            "You are the ChefByte domain agent. Use tools to manage kitchen data and planning. Return a concise answer."
        )
    )
    t0 = time.perf_counter()
    cb = ToolLogCallback()
    resp = await agent.ainvoke({"messages": [system, HumanMessage(content=user_input)]}, config={"callbacks": [cb]})
    dt = round(time.perf_counter() - t0, 3)
    messages = resp.get("messages") if isinstance(resp, dict) else None
    final_msg = messages[-1].content if messages else None
    return (str(final_msg) if final_msg is not None else None), dt, cb.tool_calls


async def run_coachbyte(user_input: str, model_name: str = "gpt-4.1") -> Tuple[Optional[str], float, List[Dict[str, Any]]]:
    agent = build_coachbyte_agent(model_name)
    system = SystemMessage(
        content=(
            "You are the CoachByte domain agent. Use ONLY the provided UI tools for workout planning and logs: "
            "new_daily_plan, get_today_plan, log_completed_set, complete_planned_set, update_summary, get_recent_history, "
            "set_weekly_split_day, get_weekly_split, set_timer, get_timer.\n"
            "If the user says to use a tool named exactly 'X', call that exact tool and return ONLY the tool's raw result.\n"
            "Extract and supply all required arguments from the user's request (e.g., build 'items' for set_weekly_split_day with exercise, reps, load, order; infer sensible defaults where appropriate).\n"
            "Do not simulate tool effects or add extra commentary."
        )
    )
    t0 = time.perf_counter()
    cb = ToolLogCallback()
    resp = await agent.ainvoke({"messages": [system, HumanMessage(content=user_input)]}, config={"callbacks": [cb]})
    dt = round(time.perf_counter() - t0, 3)
    messages = resp.get("messages") if isinstance(resp, dict) else None
    final_msg = messages[-1].content if messages else None
    return (str(final_msg) if final_msg is not None else None), dt, cb.tool_calls


