import asyncio
import os
import time
from typing import Dict, Optional, TypedDict, Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.callbacks import BaseCallbackHandler

from langchain_mcp_adapters.client import MultiServerMCPClient

# ==========================
# Configuration (edit here)
# ==========================

# Distinct models for the top-level orchestrator and specialist domain agents.
ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "gpt-4.1-mini")
SPECIALIST_MODEL = os.environ.get("SPECIALIST_MODEL", "gpt-4.1-mini")

# Timeouts (seconds) and concurrency controls
MCP_TOOL_TIMEOUT_S = float(os.environ.get("MCP_TOOL_TIMEOUT_S", "4.0"))
DOMAIN_RUN_TIMEOUT_S = float(os.environ.get("DOMAIN_RUN_TIMEOUT_S", "20.0"))
ROUTER_TIMEOUT_S = float(os.environ.get("ROUTER_TIMEOUT_S", "30.0"))
SCHEMA_BUILD_CONCURRENCY = int(os.environ.get("SCHEMA_BUILD_CONCURRENCY", "4"))
LIGHT_SCHEMA_SOURCE = os.environ.get("LIGHT_SCHEMA_SOURCE", "mcp").strip().lower()  # 'mcp' or 'file'
LIGHT_SCHEMA_FILE = os.environ.get("LIGHT_SCHEMA_FILE", "light_schema.txt")

# Configure your MCP servers here.
SERVERS: Dict[str, Dict[str, str]] = {
    "ChefByte": {"transport": "sse", "url": "http://192.168.0.226:8052/sse"},
    "GeneralByte": {"transport": "sse", "url": "http://192.168.0.226:8050/sse"},
    "HomeAssistant": {"transport": "sse", "url": "http://192.168.0.226:8051/sse"},
    "CoachByte": {"transport": "sse", "url": "http://192.168.0.226:8053/sse"},
}

# Mapping from internal domain keys to server labels
DOMAIN_TO_SERVER: Dict[str, str] = {
    "chefbyte": "ChefByte",
    "coachbyte": "CoachByte",
    "ha": "HomeAssistant",
    "general": "GeneralByte",
}


# ==========================
# Routing schema
# ==========================


class DomainSlot(BaseModel):
    instruction: Optional[str] = Field(
        default=None, description="Instruction for this domain, or None if no action"
    )


class RoutingDecision(BaseModel):
    chefbyte: DomainSlot
    coachbyte: DomainSlot
    ha: DomainSlot
    general: DomainSlot
    final_output: Optional[str] = Field(
        default=None,
        description=(
            "Final response text — only set if the orchestrator completes the request"
            " entirely without calling any domain agents"
        ),
    )


def _classify_group(tool_name: str) -> str:
    name = tool_name.strip().upper()
    if name.startswith("UPDATE"):
        return "Update tools"
    if name.startswith("GET"):
        return "Getter tools"
    if name.startswith("ACTION"):
        return "Actions tools"
    return "Other tools"


def _clean_desc(desc: str | None) -> str:
    if not desc:
        return ""
    return " ".join(str(desc).split())


def _strip_domain_prefix(tool_name: str, prefixes: list[str]) -> str:
    if not tool_name:
        return tool_name
    for p in prefixes:
        if tool_name.upper().startswith(p + "_"):
            return tool_name[len(p) + 1 :]
    return tool_name


async def build_light_schema_text() -> str:
    """Query MCP servers for tools and produce a compact, human-readable schema.

    Fetches servers concurrently and applies per-server timeouts to avoid hangs.
    """
    client = MultiServerMCPClient(SERVERS)

    async def fetch_one(server_name: str) -> tuple[str, list[str]]:
        out_lines: list[str] = []
        try:
            tools = await asyncio.wait_for(
                client.get_tools(server_name=server_name), timeout=MCP_TOOL_TIMEOUT_S
            )
        except Exception as exc:  # pragma: no cover - best-effort
            out_lines.append(server_name)
            out_lines.append("Update tools")
            out_lines.append("Getter tools")
            out_lines.append("Actions tools")
            out_lines.append(f"- error: failed to load tools ({exc})")
            out_lines.append("")
            return (server_name, out_lines)

        grouped: Dict[str, list[tuple[str, str, str]]] = {
            "Update tools": [],
            "Getter tools": [],
            "Actions tools": [],
            "Other tools": [],
        }
        domain_prefixes = ["COACH", "CHEF", "GENERAL", "HA"]
        for t in tools:
            tool_name = getattr(t, "name", "") or ""
            tool_desc = _clean_desc(getattr(t, "description", ""))
            short_name = _strip_domain_prefix(tool_name, domain_prefixes)
            grp = _classify_group(short_name)
            grouped.setdefault(grp, []).append((tool_name, short_name, tool_desc))

        for grp_label in grouped:
            grouped[grp_label].sort(key=lambda x: x[1].lower())

        out_lines.append(server_name)
        for grp_label in ("Update tools", "Getter tools", "Actions tools"):
            out_lines.append(grp_label)
            if grouped[grp_label]:
                for orig_name, _short, desc in grouped[grp_label]:
                    out_lines.append(f"- {orig_name}: {desc}" if desc else f"- {orig_name}:")
            out_lines.append("")

        if grouped["Other tools"]:
            out_lines.append("Other tools")
            for orig_name, _short, desc in grouped["Other tools"]:
                out_lines.append(f"- {orig_name}: {desc}" if desc else f"- {orig_name}:")
            out_lines.append("")

        return (server_name, out_lines)

    sem = asyncio.Semaphore(SCHEMA_BUILD_CONCURRENCY)

    async def bounded_fetch(name: str):
        async with sem:
            return await fetch_one(name)

    coros = [bounded_fetch(name) for name in SERVERS.keys()]
    results = await asyncio.gather(*coros, return_exceptions=True)

    lines: list[str] = []
    # preserve order of SERVERS
    tmp: Dict[str, list[str]] = {}
    for item in results:
        if isinstance(item, Exception):
            # Unusual, but write a minimal section
            continue
        name, out_lines = item
        tmp[name] = out_lines

    for name in SERVERS.keys():
        if name in tmp:
            lines.extend(tmp[name])
        else:
            lines.append(name)
            lines.append("Update tools")
            lines.append("Getter tools")
            lines.append("Actions tools")
            lines.append("- error: failed to load tools (unknown)")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def make_router_system_prompt(light_schema: str) -> str:
    return (
        "You are an orchestrator. You receive a high-level tool graph (light schema) with minimal descriptions.\n"
        "Your task: split the user input into per-domain instructions.\n"
        "- Only assign an instruction to a domain if it is appropriate based on the tool summaries.\n"
        "- Keep it concise and actionable per domain.\n"
        "- If a domain has nothing to do, set its 'instruction' to null.\n"
        "- Additionally the JSON includes a 'final_output' field:\n"
        "    * ONLY set 'final_output' when the orchestrator has completed the user request entirely itself and does NOT need to call any domain agents.\n"
        "    * If the request must be handled by one or more domain agents, leave 'final_output' null and place per-domain instructions instead.\n"
        "Light schema (read-only context):\n\n"
        f"{light_schema}\n"
        "Output must be a JSON object matching this Pydantic model: RoutingDecision with fields: chefbyte, coachbyte, ha, general, final_output.\n"
        "Each domain field is an object with optional 'instruction' (string or null).\n"
        "Set 'final_output' only when no domain calls are required; otherwise keep it null.\n"
        "Do not include extra fields.\n"
    )


async def route_query(user_input: str, light_schema: str) -> RoutingDecision:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set.")

    # Prefer structured output if available
    model = ChatOpenAI(model=ORCHESTRATOR_MODEL)

    try:
        structured = getattr(model, "with_structured_output", None)
        if structured is not None:
            router = model.with_structured_output(RoutingDecision)
            return await asyncio.wait_for(
                router.ainvoke(
                [
                    SystemMessage(content=make_router_system_prompt(light_schema)),
                    HumanMessage(content=user_input),
                ]
                ),
                timeout=ROUTER_TIMEOUT_S,
            )
    except Exception:  # pragma: no cover - version feature probe
        pass

    # Fallback: use a parser if available, otherwise naive JSON extraction
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import PydanticOutputParser

        parser = PydanticOutputParser(pydantic_object=RoutingDecision)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", make_router_system_prompt(light_schema)),
                ("human", "{user_input}\n\n{format_instructions}"),
            ]
        ).partial(format_instructions=parser.get_format_instructions())
        chain = prompt | model | parser
        return await asyncio.wait_for(
            chain.ainvoke({"user_input": user_input}), timeout=ROUTER_TIMEOUT_S
        )
    except Exception:  # pragma: no cover - last-resort
        resp = await asyncio.wait_for(
            model.ainvoke(
            [
                SystemMessage(content=make_router_system_prompt(light_schema)),
                HumanMessage(content=user_input),
            ]
            ),
            timeout=ROUTER_TIMEOUT_S,
        )
        content = str(resp.content)
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return JSON.")
        import json

        data = json.loads(content[start : end + 1])
        return RoutingDecision.model_validate(data)


# ==========================
# Domain execution helpers
# ==========================


_agent_cache: Dict[str, object] = {}
_agent_cache_lock = asyncio.Lock()
_tool_list_s_by_server: Dict[str, float] = {}


async def _build_domain_agent(server_label: str):
    """Build or reuse a ReAct agent bound to a single server's tools."""
    async with _agent_cache_lock:
        if server_label in _agent_cache:
            return _agent_cache[server_label]

        model = ChatOpenAI(model=SPECIALIST_MODEL)
        client = MultiServerMCPClient({server_label: SERVERS[server_label]})
        t0_list = time.perf_counter()
        tools = await asyncio.wait_for(
            client.get_tools(server_name=server_label), timeout=MCP_TOOL_TIMEOUT_S
        )
        _tool_list_s_by_server[server_label] = round(time.perf_counter() - t0_list, 3)
        agent = create_react_agent(model, tools)
        _agent_cache[server_label] = agent
        return agent


class ToolTimingCallback(BaseCallbackHandler):
    """Collect per-tool call durations during agent execution."""

    def __init__(self) -> None:
        self._starts: Dict[Any, tuple[float, str]] = {}
        self.tool_calls: list[dict[str, Any]] = []

    def on_tool_start(self, serialized, input_str, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
        try:
            name = None
            if isinstance(serialized, dict):
                name = serialized.get("name") or serialized.get("id")
            if not name:
                name = str(serialized)
        except Exception:
            name = "<unknown_tool>"
        self._starts[run_id] = (time.perf_counter(), str(name))

    def on_tool_end(self, output, run_id, **kwargs):  # type: ignore[override]
        start, name = self._starts.pop(run_id, (None, None))
        if start is not None:
            self.tool_calls.append(
                {"name": name, "duration_s": round(time.perf_counter() - start, 3)}
            )

    def on_tool_error(self, error, run_id, **kwargs):  # type: ignore[override]
        start, name = self._starts.pop(run_id, (None, None))
        if start is not None:
            self.tool_calls.append(
                {
                    "name": name,
                    "duration_s": round(time.perf_counter() - start, 3),
                    "error": str(error),
                }
            )


async def _run_one_domain(server_label: str, instruction: str) -> tuple[str, Dict[str, Any]]:
    agent = await _build_domain_agent(server_label)
    system = SystemMessage(
        content=(
            f"You are the {server_label} domain agent. Fulfill the user's instruction using your available tools. "
            "Think step-by-step and stop when done."
        )
    )
    cb = ToolTimingCallback()
    t0 = time.perf_counter()
    try:
        resp = await asyncio.wait_for(
            agent.ainvoke({"messages": [system, HumanMessage(content=instruction)]}, config={"callbacks": [cb]}),
            timeout=DOMAIN_RUN_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        return "ERROR: domain execution timed out", {"run_s": round(time.perf_counter() - t0, 3), "tool_calls": cb.tool_calls}
    run_s = time.perf_counter() - t0
    messages = resp["messages"]
    return (
        messages[-1].content if messages else "",
        {
            "run_s": round(run_s, 3),
            "tool_calls": cb.tool_calls,
            "tool_list_s": _tool_list_s_by_server.get(server_label),
        },
    )


# ==========================
# Orchestrator graph
# ==========================


class OrchestratorState(TypedDict, total=False):
    user_input: str
    decision: RoutingDecision
    domain_results: Dict[str, Optional[str]]
    final_output: Optional[str]
    timings: Dict[str, Any]


_schema_cache: Optional[str] = None
_schema_lock = asyncio.Lock()


async def _get_light_schema() -> str:
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache
    async with _schema_lock:
        if _schema_cache is None:
            if LIGHT_SCHEMA_SOURCE == "file":
                try:
                    with open(LIGHT_SCHEMA_FILE, "r", encoding="utf-8") as f:
                        _schema_cache = f.read()
                except Exception:
                    # fallback to live fetch
                    _schema_cache = await build_light_schema_text()
            else:
                _schema_cache = await build_light_schema_text()
    return _schema_cache


async def router_node(state: OrchestratorState) -> OrchestratorState:
    t0 = time.perf_counter()
    light_schema = await _get_light_schema()
    decision = await route_query(state["user_input"], light_schema)
    return {
        "decision": decision,
        "timings": {"routing_s": round(time.perf_counter() - t0, 3)},
    }


async def domains_node(state: OrchestratorState) -> OrchestratorState:
    dec = state["decision"]
    tasks: Dict[str, asyncio.Task[Any]] = {}
    for domain_key, slot in (
        ("chefbyte", dec.chefbyte),
        ("coachbyte", dec.coachbyte),
        ("ha", dec.ha),
        ("general", dec.general),
    ):
        if slot and slot.instruction:
            server_label = DOMAIN_TO_SERVER[domain_key]
            tasks[domain_key] = asyncio.create_task(
                _run_one_domain(server_label, slot.instruction)
            )

    results: Dict[str, Optional[str]] = {
        "chefbyte": None,
        "coachbyte": None,
        "ha": None,
        "general": None,
    }

    t0 = time.perf_counter()
    if tasks:
        done = await asyncio.gather(*tasks.values(), return_exceptions=True)
        domain_details: Dict[str, Any] = {}
        for domain_key, value in zip(tasks.keys(), done):
            if isinstance(value, Exception):
                results[domain_key] = f"ERROR: {value}"
            else:
                if isinstance(value, tuple) and len(value) == 2:
                    results[domain_key] = value[0]
                    domain_details[domain_key] = value[1]
                else:
                    results[domain_key] = value
    return {
        "domain_results": results,
        "timings": {
            **state.get("timings", {}),
            "domains_total_s": round(time.perf_counter() - t0, 3),
            "domain_details": domain_details if 'domain_details' in locals() else {},
        },
    }


async def synth_node(state: OrchestratorState) -> OrchestratorState:
    dec = state["decision"]
    if dec.final_output:
        return {
            "final_output": dec.final_output,
            "timings": {**state.get("timings", {}), "synthesis_s": 0.0},
        }

    model = ChatOpenAI(model=ORCHESTRATOR_MODEL)
    r = state["domain_results"]
    synth_system = SystemMessage(
        content=(
            "You are the top-level orchestrator. Compose a concise final reply to the user, using the domain results below. "
            "Only include necessary information in the final answer."
        )
    )
    synth_human = HumanMessage(
        content=(
            f"User input: {state['user_input']}\n\n"
            f"Domain results:\n"
            f"- ChefByte: {r.get('chefbyte')}\n"
            f"- CoachByte: {r.get('coachbyte')}\n"
            f"- HomeAssistant: {r.get('ha')}\n"
            f"- GeneralByte: {r.get('general')}\n"
        )
    )
    t0 = time.perf_counter()
    resp = await model.ainvoke([synth_system, synth_human])
    final_output = str(resp.content).strip()
    return {
        "final_output": final_output,
        "timings": {**state.get("timings", {}), "synthesis_s": round(time.perf_counter() - t0, 3)},
    }


def get_orchestrator_app():
    g = StateGraph(OrchestratorState)
    g.add_node("route", router_node)
    g.add_node("run_domains", domains_node)
    g.add_node("synthesize", synth_node)
    g.set_entry_point("route")
    g.add_edge("route", "run_domains")
    g.add_edge("run_domains", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


async def orchestrate(user_input: str) -> dict:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set.")

    app = get_orchestrator_app()
    t0_total = time.perf_counter()
    out = await app.ainvoke({"user_input": user_input})
    dec: RoutingDecision = out["decision"]
    return {
        "chefbyte": dec.chefbyte.instruction,
        "coachbyte": dec.coachbyte.instruction,
        "ha": dec.ha.instruction,
        "general": dec.general.instruction,
        "domain_results": out.get("domain_results"),
        "final_output": out.get("final_output"),
        "timings": {
            **(out.get("timings") or {}),
            "total_s": round(time.perf_counter() - t0_total, 3),
        },
        # include models used for transparency
        "models": {
            "orchestrator": ORCHESTRATOR_MODEL,
            "specialist": SPECIALIST_MODEL,
        },
    }


# This module intentionally omits CLI to keep it focused and importable.


