import os
import sys
import json
import time
import asyncio
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
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.callbacks.base import BaseCallbackHandler

from core.helpers.light_schema_gen import discover_extensions, build_all_light_schema  # noqa: E402
from core.helpers.llm_selector import get_chat_model  # noqa: E402


# ---- Models ----
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


class ToolCallOptions(BaseModel):
    passthrough: bool = True


class PlannedToolCall(BaseModel):
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    options: ToolCallOptions = Field(default_factory=ToolCallOptions)


class PlannerStep(BaseModel):
    calls: List[PlannedToolCall] = Field(default_factory=list)
    # Optional final text for when no further tool use is needed
    final_text: Optional[str] = None


class ToolResult(BaseModel):
    tool: str
    args: Optional[Dict[str, Any]] = None
    success: bool = True
    public_text: str
    error: Optional[str] = None
    duration_secs: Optional[float] = None


# ---- Runtime cache ----
RUN_TRACES: List[ToolTrace] = []
TOOL_RUNNERS: Dict[str, Any] = {}
LIGHT_SCHEMA: str = ""
DOMAIN_PROMPTS_TEXT: str = ""


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    return val if isinstance(val, str) and val.strip() else default


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in {"1", "true", "yes", "on"}:
            return True
        if v in {"0", "false", "no", "off"}:
            return False
    return bool(default)


def _dbg_enabled() -> bool:
    # Default to True so you can see logs unless explicitly disabled
    return _env_bool("MONO_PT_DEBUG", True)


def _truncate(text: str, max_len: int) -> str:
    try:
        if not isinstance(text, str):
            text = str(text)
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."
    except Exception:
        return str(text)


def _dbg_print(msg: str) -> None:
    if _dbg_enabled():
        try:
            print(msg)
        except Exception:
            pass


class LLMRunTracer(BaseCallbackHandler):
    def __init__(self, key: str):
        self.key = key
        self._starts: Dict[str, float] = {}
        self.total_duration_secs: float = 0.0

    def on_llm_start(self, serialized, prompts, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
        try:
            self._starts[str(run_id)] = time.perf_counter()
        except Exception:
            pass

    def on_llm_end(self, response, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
        try:
            start = self._starts.pop(str(run_id), None)
            if isinstance(start, (int, float)):
                self.total_duration_secs += max(0.0, time.perf_counter() - start)
        except Exception:
            pass


def _normalize_result_to_string(result: Any) -> str:
    if isinstance(result, BaseModel):
        # Prefer portable JSON dump
        try:
            return json.dumps(result.model_dump(), ensure_ascii=False)
        except Exception:
            try:
                return result.model_dump_json()  # type: ignore[attr-defined]
            except Exception:
                try:
                    return result.json()  # type: ignore[attr-defined]
                except Exception:
                    return str(result)
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return str(result)
    return str(result)


def _wrap_callable_as_runner(fn, ext_name: str):
    """Wrap a tool function to return a structured ToolResult.

    Hardcode success=True unless an exception is raised; on exception, success=False
    and the error message is returned in both public_text and error fields.
    """

    # Build a minimal signature for planner docs (not strictly required for runtime)
    try:
        sig = inspect.signature(fn)
        hints = get_type_hints(fn, globalns=getattr(fn, "__globals__", {}))
    except Exception:
        sig = None
        hints = {}

    def _runner(**kwargs) -> ToolResult:
        t0 = time.perf_counter()
        try:
            result = fn(**kwargs)
            sres = _normalize_result_to_string(result)
            dur = time.perf_counter() - t0
            # success=True by default per requirement
            RUN_TRACES.append(ToolTrace(tool=fn.__name__, args=(kwargs or None), output=sres, duration_secs=dur))
            return ToolResult(tool=fn.__name__, args=(kwargs or None), success=True, public_text=sres, error=None, duration_secs=dur)
        except Exception as e:
            # On exception, mark failure; include error text in output for visibility
            err = f"Error running tool {fn.__name__}: {str(e)}"
            try:
                dur = time.perf_counter() - t0
            except Exception:
                dur = None
            RUN_TRACES.append(ToolTrace(tool=fn.__name__, args=(kwargs or None), output=err, duration_secs=dur))
            return ToolResult(tool=fn.__name__, args=(kwargs or None), success=False, public_text=err, error=str(e), duration_secs=dur)

    # Attach minimal docs metadata for potential future use
    _runner.__doc__ = inspect.getdoc(fn) or ""
    _runner.__name__ = fn.__name__
    _runner.__signature__ = getattr(fn, "__signature__", None) or sig  # type: ignore[attr-defined]
    _runner.__annotations__ = getattr(fn, "__annotations__", {}) or hints
    return _runner


def initialize_runtime(tool_root: Optional[str] = None) -> None:
    global TOOL_RUNNERS, LIGHT_SCHEMA, DOMAIN_PROMPTS_TEXT
    TOOL_RUNNERS = {}
    try:
        exts = discover_extensions(tool_root)
    except Exception:
        exts = []
    # Build tool runners and collect domain prompts
    domain_prompts: List[str] = []
    for ext in exts:
        for fn in (ext.get("tools") or []):
            try:
                runner = _wrap_callable_as_runner(fn, ext.get("name", "unknown"))
                TOOL_RUNNERS[fn.__name__] = runner
            except Exception:
                continue
        # Append full system prompt section per domain
        try:
            name = ext.get("name", "")
            sp = ext.get("system_prompt", "")
            if isinstance(name, str) and isinstance(sp, str) and sp.strip():
                domain_prompts.append(f"[Domain: {name}]\n{sp.strip()}")
        except Exception:
            pass
    try:
        LIGHT_SCHEMA = build_all_light_schema()
    except Exception:
        LIGHT_SCHEMA = ""
    try:
        DOMAIN_PROMPTS_TEXT = "\n\n".join([p for p in domain_prompts if p])
    except Exception:
        DOMAIN_PROMPTS_TEXT = ""


def _active_models() -> Dict[str, str]:
    return {
        "router": "",
        "domain": _get_env("MONO_PT_PLANNER_MODEL", _get_env("REACT_MODEL", "gpt-4.1") ) or "gpt-4.1",
        "synth": "",
    }


def _build_planner_messages(user_prompt: str, chat_history: Optional[str], memory: Optional[str], light_schema: str, review_items: Optional[List[ToolResult]] = None) -> List[Any]:
    system_lines: List[str] = []
    system_lines.append("You are a planning agent that ONLY returns JSON.")
    system_lines.append("Plan tool calls. Output strictly this JSON schema:")
    system_lines.append('{"calls": [{"tool": "<name>", "args": {...}, "options": {"passthrough": true|false}}], "final_text": null | "<text>"}')
    system_lines.append("- passthrough defaults to true if omitted.")
    system_lines.append("- Passthrough policy: Default passthrough=true. Set passthrough=false ONLY when you must read the tool output to choose or parameterize your next call. Otherwise, keep passthrough=true to stream results directly.")
    system_lines.append("- Most tool calls should use passthrough=true.")
    system_lines.append("- Use final_text only when finishing; otherwise omit or set null.")
    system_lines.append("- Prefer batching independent calls in the same step.")
    system_lines.append("")
    if light_schema.strip():
        system_lines.append("Available tools:")
        system_lines.append(light_schema.strip())
    # Optionally include full domain prompts for better guidance
    try:
        if _env_bool("MONO_PT_INCLUDE_DOMAIN_PROMPTS", True) and DOMAIN_PROMPTS_TEXT.strip():
            system_lines.append("")
            system_lines.append("Domain system prompts:")
            system_lines.append(DOMAIN_PROMPTS_TEXT.strip())
    except Exception:
        pass
    if isinstance(review_items, list) and review_items:
        system_lines.append("")
        system_lines.append("Context: You are in a follow-up step. Some results require review.")
    sys_text = "\n".join(system_lines)

    msgs: List[Any] = [SystemMessage(content=sys_text)]
    if chat_history or memory:
        msgs.append(SystemMessage(content=(
            "Conversation context to consider when planning.\n"
            f"Chat history:\n{chat_history or ''}\n\n"
            f"Memory:\n{memory or ''}"
        )))
    if isinstance(review_items, list) and review_items:
        # Provide only the items that need review (non-passthrough or failures)
        review_payload = []
        for r in review_items:
            review_payload.append({
                "tool": r.tool,
                "success": bool(r.success),
                "public_text": r.public_text,
                "error": r.error,
            })
        msgs.append(SystemMessage(content=(
            "Items requiring review (non-passthrough or failed):\n" + json.dumps(review_payload, ensure_ascii=False)
        )))
    msgs.append(HumanMessage(content=user_prompt))
    return msgs


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    # Try direct JSON first
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # Fallback: find first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        snippet = text[start : end + 1]
        try:
            obj = json.loads(snippet)
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
    return None


async def _run_one_tool(name: str, args: Dict[str, Any]) -> ToolResult:
    runner = TOOL_RUNNERS.get(name)
    if runner is None:
        # Tool not found — return failure immediately
        return ToolResult(tool=name, args=args or None, success=False, public_text=f"Error: unknown tool '{name}'", error="unknown tool", duration_secs=None)
    # Run potentially blocking tool in a worker thread
    return await asyncio.to_thread(runner, **(args or {}))


async def _execute_planned_calls(calls: List[PlannedToolCall]) -> Tuple[List[ToolResult], List[Tuple[PlannedToolCall, ToolResult]]]:
    tasks = [asyncio.create_task(_run_one_tool(pc.tool, pc.args or {})) for pc in calls]
    results: List[ToolResult] = await asyncio.gather(*tasks)
    # Pair each result with its plan call for routing
    paired: List[Tuple[PlannedToolCall, ToolResult]] = list(zip(calls, results))
    return results, paired


async def run_agent(user_prompt: str, chat_history: Optional[str] = None, memory: Optional[str] = None, tool_root: Optional[str] = None, llm: Optional[str] = None) -> AgentResult:
    # Prepare tools once
    if not TOOL_RUNNERS or isinstance(tool_root, str):
        initialize_runtime(tool_root=tool_root)
    if not TOOL_RUNNERS:
        msg = "No tools discovered. Ensure files matching *_tool.py exist under extensions/."
        return AgentResult(final=msg, results=[], timings=[], content=msg, response_time_secs=0.0, traces=[])

    # Planner model: use tier if provided; otherwise env-based model
    tracer = LLMRunTracer("planner")
    if isinstance(llm, str) and llm.strip() in {"low", "med", "high"}:
        model = get_chat_model(role="domain", tier=llm.strip(), callbacks=[tracer], temperature=0.0)
    else:
        planner_model_name = _get_env("MONO_PT_PLANNER_MODEL", _get_env("REACT_MODEL", "gpt-4.1")) or "gpt-4.1"
        model = get_chat_model(role="domain", model=planner_model_name, callbacks=[tracer], temperature=0.0)

    # Clear traces per run
    del RUN_TRACES[:]

    # Iterative plan-execute-review loop
    t0_total = time.perf_counter()
    accumulated_segments: List[str] = []
    timings: List[Timing] = []
    recursion_limit = int(_get_env("MONO_PT_RECURSION_LIMIT", "8") or 8)
    followup_items: List[ToolResult] = []
    step = 0

    while step < recursion_limit:
        step += 1
        # Build planning messages (initial or follow-up)
        messages = _build_planner_messages(
            user_prompt=user_prompt,
            chat_history=chat_history,
            memory=memory,
            light_schema=LIGHT_SCHEMA,
            review_items=(followup_items or None),
        )

        # Invoke planner
        t0_plan = time.perf_counter()
        _dbg_print(f"[simple-pt] step {step}: planning...")
        plan_resp = await model.ainvoke(messages)
        plan_secs = time.perf_counter() - t0_plan
        timings.append(Timing(name=f"plan:{step}", seconds=float(plan_secs)))
        # Parse plan JSON
        raw_text = (plan_resp.content or "") if hasattr(plan_resp, "content") else str(plan_resp)
        _dbg_print(f"[simple-pt] step {step}: planner raw -> {_truncate(raw_text, int(_get_env('MONO_PT_LOG_MAXLEN', '600') or '600'))}")
        parsed = _extract_json_object(raw_text)
        planner_step = PlannerStep()
        if isinstance(parsed, dict):
            try:
                planner_step = PlannerStep.model_validate(parsed)
            except Exception:
                # Try to coerce structure
                calls_raw = parsed.get("calls") if isinstance(parsed.get("calls"), list) else []
                calls: List[PlannedToolCall] = []
                for c in calls_raw:
                    try:
                        calls.append(PlannedToolCall.model_validate(c))
                    except Exception:
                        continue
                planner_step = PlannerStep(calls=calls, final_text=parsed.get("final_text"))

        # If planner provided final text only and no calls, finish
        if not planner_step.calls:
            if isinstance(planner_step.final_text, str) and planner_step.final_text.strip():
                accumulated_segments.append(planner_step.final_text.strip())
                _dbg_print(f"[simple-pt] step {step}: final_text provided; finishing.")
            break

        # Execute calls concurrently
        _dbg_print(f"[simple-pt] step {step}: executing {len(planner_step.calls)} call(s) concurrently...")
        for idx, pc in enumerate(planner_step.calls, start=1):
            try:
                args_str = json.dumps(pc.args or {}, ensure_ascii=False)
            except Exception:
                args_str = str(pc.args or {})
            _dbg_print(f"[simple-pt] step {step} CALL {idx}/{len(planner_step.calls)}: tool={pc.tool} passthrough={(pc.options.passthrough if pc.options else True)} args={_truncate(args_str, int(_get_env('MONO_PT_LOG_MAXLEN', '600') or '600'))}")

        t0_exec = time.perf_counter()
        _, paired = await _execute_planned_calls(planner_step.calls)
        exec_secs = time.perf_counter() - t0_exec
        timings.append(Timing(name=f"exec:{step}", seconds=float(exec_secs)))

        # Route outputs
        followup_items = []
        for idx, (pc, res) in enumerate(paired, start=1):
            passthrough = True if pc.options is None else bool(getattr(pc.options, "passthrough", True))
            if passthrough and res.success:
                # Stream directly by appending to segments
                if isinstance(res.public_text, str) and res.public_text.strip():
                    accumulated_segments.append(res.public_text.strip())
                _dbg_print(f"[simple-pt] step {step} RESULT {idx}/{len(paired)}: tool={res.tool} success={res.success} passthrough={passthrough} ROUTE=STREAMED text={_truncate(res.public_text, int(_get_env('MONO_PT_LOG_MAXLEN', '600') or '600'))}")
            else:
                followup_items.append(res)
                _dbg_print(f"[simple-pt] step {step} RESULT {idx}/{len(paired)}: tool={res.tool} success={res.success} passthrough={passthrough} ROUTE=REVIEW text={_truncate(res.public_text, int(_get_env('MONO_PT_LOG_MAXLEN', '600') or '600'))}")

        # If nothing needs review, continue next plan step
        if not followup_items:
            _dbg_print(f"[simple-pt] step {step}: no follow-up needed; finishing.")
            break

        # Otherwise, perform a follow-up planning turn over just the items needing review
        # The loop will rebuild messages with review_items and iterate

    total_secs = time.perf_counter() - t0_total
    timings.append(Timing(name="total", seconds=float(total_secs)))

    final_text = "\n\n".join([seg for seg in accumulated_segments if isinstance(seg, str) and seg])
    _dbg_print(f"[simple-pt] done. steps={step} segments={len(accumulated_segments)} total={total_secs:.2f}s")
    return AgentResult(
        final=final_text,
        results=[],
        timings=timings,
        content=final_text,
        response_time_secs=float(total_secs),
        traces=list(RUN_TRACES),
    )


async def run_agent_stream(user_prompt: str, chat_history: Optional[str] = None, memory: Optional[str] = None, tool_root: Optional[str] = None, llm: Optional[str] = None):
    """Yield incremental text chunks while the agent generates a response.

    For this planner-executor architecture, we stream tool results as they complete.
    Fallback: if streaming is unavailable, yields the final response once.
    """
    # Prepare tools once
    if not TOOL_RUNNERS or isinstance(tool_root, str):
        initialize_runtime(tool_root=tool_root)
    if not TOOL_RUNNERS:
        yield "No tools discovered. Ensure files matching *_tool.py exist under extensions/."
        return

    # Planner model: use tier if provided; otherwise env-based model
    tracer = LLMRunTracer("planner")
    if isinstance(llm, str) and llm.strip() in {"low", "med", "high"}:
        model = get_chat_model(role="domain", tier=llm.strip(), callbacks=[tracer], temperature=0.0)
    else:
        planner_model_name = _get_env("MONO_PT_PLANNER_MODEL", _get_env("REACT_MODEL", "gpt-4.1")) or "gpt-4.1"
        model = get_chat_model(role="domain", model=planner_model_name, callbacks=[tracer], temperature=0.0)

    # Clear traces per run
    del RUN_TRACES[:]

    # Iterative plan-execute-review loop with streaming
    accumulated_segments: List[str] = []
    recursion_limit = int(_get_env("MONO_PT_RECURSION_LIMIT", "8") or 8)
    followup_items: List[ToolResult] = []
    step = 0
    yielded_any = False

    while step < recursion_limit:
        step += 1
        # Build planning messages (initial or follow-up)
        messages = _build_planner_messages(
            user_prompt=user_prompt,
            chat_history=chat_history,
            memory=memory,
            light_schema=LIGHT_SCHEMA,
            review_items=(followup_items or None),
        )

        # Invoke planner
        _dbg_print(f"[simple-pt-stream] step {step}: planning...")
        plan_resp = await model.ainvoke(messages)
        
        # Parse plan JSON
        raw_text = (plan_resp.content or "") if hasattr(plan_resp, "content") else str(plan_resp)
        _dbg_print(f"[simple-pt-stream] step {step}: planner raw -> {_truncate(raw_text, int(_get_env('MONO_PT_LOG_MAXLEN', '600') or '600'))}")
        parsed = _extract_json_object(raw_text)
        planner_step = PlannerStep()
        if isinstance(parsed, dict):
            try:
                planner_step = PlannerStep.model_validate(parsed)
            except Exception:
                # Try to coerce structure
                calls_raw = parsed.get("calls") if isinstance(parsed.get("calls"), list) else []
                calls: List[PlannedToolCall] = []
                for c in calls_raw:
                    try:
                        calls.append(PlannedToolCall.model_validate(c))
                    except Exception:
                        continue
                planner_step = PlannerStep(calls=calls, final_text=parsed.get("final_text"))

        # If planner provided final text only and no calls, finish
        if not planner_step.calls:
            if isinstance(planner_step.final_text, str) and planner_step.final_text.strip():
                final_chunk = planner_step.final_text.strip()
                accumulated_segments.append(final_chunk)
                yield final_chunk
                yielded_any = True
                _dbg_print(f"[simple-pt-stream] step {step}: final_text provided; finishing.")
            break

        # Execute calls concurrently
        _dbg_print(f"[simple-pt-stream] step {step}: executing {len(planner_step.calls)} call(s) concurrently...")
        for idx, pc in enumerate(planner_step.calls, start=1):
            try:
                args_str = json.dumps(pc.args or {}, ensure_ascii=False)
            except Exception:
                args_str = str(pc.args or {})
            _dbg_print(f"[simple-pt-stream] step {step} CALL {idx}/{len(planner_step.calls)}: tool={pc.tool} passthrough={(pc.options.passthrough if pc.options else True)} args={_truncate(args_str, int(_get_env('MONO_PT_LOG_MAXLEN', '600') or '600'))}")

        _, paired = await _execute_planned_calls(planner_step.calls)

        # Route outputs and stream passthrough results
        followup_items = []
        for idx, (pc, res) in enumerate(paired, start=1):
            passthrough = True if pc.options is None else bool(getattr(pc.options, "passthrough", True))
            if passthrough and res.success:
                # Stream directly by yielding
                if isinstance(res.public_text, str) and res.public_text.strip():
                    chunk_text = res.public_text.strip()
                    accumulated_segments.append(chunk_text)
                    yield chunk_text
                    yielded_any = True
                _dbg_print(f"[simple-pt-stream] step {step} RESULT {idx}/{len(paired)}: tool={res.tool} success={res.success} passthrough={passthrough} ROUTE=STREAMED text={_truncate(res.public_text, int(_get_env('MONO_PT_LOG_MAXLEN', '600') or '600'))}")
            else:
                followup_items.append(res)
                _dbg_print(f"[simple-pt-stream] step {step} RESULT {idx}/{len(paired)}: tool={res.tool} success={res.success} passthrough={passthrough} ROUTE=REVIEW text={_truncate(res.public_text, int(_get_env('MONO_PT_LOG_MAXLEN', '600') or '600'))}")

        # If nothing needs review, continue next plan step
        if not followup_items:
            _dbg_print(f"[simple-pt-stream] step {step}: no follow-up needed; finishing.")
            break

    if not yielded_any:
        # Fallback to non-streaming execution
        _dbg_print("[simple-pt-stream] no content streamed; falling back to non-streaming.")
        res = await run_agent(user_prompt, chat_history=chat_history, memory=memory, tool_root=tool_root, llm=llm)
        yield res.final
        return

    _dbg_print(f"[simple-pt-stream] done. steps={step} segments={len(accumulated_segments)}")


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Simple passthough agent over all tools")
    parser.add_argument("-p", "--prompt", type=str, default="what can you do?", help="Test prompt")
    parser.add_argument("-r", "--tool-root", type=str, default=None, help="Optional root directory to discover tools under")
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



