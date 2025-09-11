import os
import sys
import json
import argparse
import asyncio
import inspect
import time
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Callable, Optional, Tuple, get_type_hints

# Load environment variables from .env if present
try:
	from dotenv import load_dotenv  # type: ignore
	load_dotenv()
except Exception:
	pass

# Ensure project root on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

from core.helpers.light_schema_gen import discover_extensions, build_light_schema_for_extension  # noqa: E402
from core.helpers.llm_selector import get_chat_model  # noqa: E402
from langchain_core.callbacks.base import BaseCallbackHandler  # noqa: E402
from pydantic import BaseModel, Field, ValidationError, create_model  # noqa: E402

# Declared model names (supported/used by the agent)
MODEL_GPT_41_MINI = "gpt-4.1-mini"
MODEL_GPT_41_NANO = "gpt-4.1-nano"
MODEL_GPT_41 = "gpt-4.1"
MODEL_GEMINI_25_FLASH = "gemini-2.5-flash"
MODEL_GEMINI_25_FLASH_LITE = "gemini-2.5-flash-lite"

# Default selections per role (can be overridden via env: ROUTER_MODEL/DOMAIN_MODEL/SYNTH_MODEL or LLM_DEFAULT_MODEL)
DEFAULT_ROUTER_MODEL = MODEL_GEMINI_25_FLASH_LITE
DEFAULT_DOMAIN_MODEL = MODEL_GEMINI_25_FLASH_LITE
DEFAULT_SYNTH_MODEL = MODEL_GEMINI_25_FLASH_LITE

# DEFAULT_ROUTER_MODEL = MODEL_GEMINI_25_FLASH
# DEFAULT_DOMAIN_MODEL = MODEL_GEMINI_25_FLASH
# DEFAULT_SYNTH_MODEL = MODEL_GEMINI_25_FLASH

# DEFAULT_ROUTER_MODEL = MODEL_GPT_41_MINI
# DEFAULT_DOMAIN_MODEL = MODEL_GPT_41_MINI
# DEFAULT_SYNTH_MODEL = MODEL_GPT_41_NANO

DEFAULT_ROUTER_MODEL = MODEL_GPT_41
DEFAULT_DOMAIN_MODEL = MODEL_GPT_41
DEFAULT_SYNTH_MODEL = MODEL_GPT_41_NANO

def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
	val = os.getenv(key)
	return val if isinstance(val, str) and val.strip() else default


def _load_llm_for_role(role: str, callbacks: Optional[List[Any]] = None):
	# Prefer role-specific env var if present, else default selection in helper
	explicit = _get_env(f"{role.upper()}_MODEL")
	if not explicit:
		explicit = _resolve_active_model_for_role(role)
	# Reuse cached LLMs per role+model combo when no callbacks are provided
	try:
		key = f"llm:{role}:{explicit}"
		if callbacks and len(callbacks) > 0:
			return get_chat_model(role=role, model=explicit, callbacks=callbacks, temperature=0.0)
		if key not in PRELOADED_LLM:
			PRELOADED_LLM[key] = get_chat_model(role=role, model=explicit, callbacks=[], temperature=0.0)
		return PRELOADED_LLM[key]
	except Exception:
		return get_chat_model(role=role, model=explicit, callbacks=(callbacks or []), temperature=0.0)


def _resolve_active_model_for_role(role: str) -> str:
	# Resolution: ROLE_MODEL env > LLM_DEFAULT_MODEL > per-role default > hard default
	val = _get_env(f"{role.upper()}_MODEL")
	if val:
		return val
	default_all = _get_env("LLM_DEFAULT_MODEL")
	if default_all:
		return default_all
	if role == "router":
		return DEFAULT_ROUTER_MODEL
	if role == "domain":
		return DEFAULT_DOMAIN_MODEL
	if role == "synth":
		return DEFAULT_SYNTH_MODEL
	return "gemini-2.5-flash-lite"


def _active_models() -> Dict[str, str]:
	return {
		"router": _resolve_active_model_for_role("router"),
		"domain": _resolve_active_model_for_role("domain"),
		"synth": _resolve_active_model_for_role("synth"),
	}


def _current_date_line() -> str:
	"""Return a single-line ISO date string for system prompts."""
	try:
		return f"Date: {datetime.now().strftime('%Y-%m-%d')}"
	except Exception:
		# Fallback to time module if datetime fails for any reason
		return f"Date: {time.strftime('%Y-%m-%d')}"


def _with_date_prefix(content: str) -> str:
	"""Prefix content with the current date on the first line."""
	return f"{_current_date_line()}\n{content}" if content else _current_date_line()


def _doc_summary_and_example(fn: Callable[..., Any]) -> Dict[str, str]:
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


TOOL_TRACES: Dict[str, List[Dict[str, Any]]] = {}
LLM_TRACES: Dict[str, List[Dict[str, Any]]] = {}
# Track LLM durations per tracer key (seconds)
LLM_DURATIONS: Dict[str, List[float]] = {}
# Preloaded extensions and schema to avoid per-turn setup overhead
PRELOADED_EXTENSIONS: Optional[List[Dict[str, Any]]] = None
PRELOADED_SCHEMA: Optional[str] = None
PRELOADED_TOOL_ROOT: Optional[str] = None
PRELOADED_LLM: Dict[str, Any] = {}


class LLMRunTracer(BaseCallbackHandler):
	def __init__(self, key: str):
		self.key = key
		self._pending: Dict[str, List[int]] = {}
		self._starts: Dict[str, float] = {}

	def on_llm_start(self, serialized, prompts, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
		idxs: List[int] = []
		for p in prompts:
			LLM_TRACES.setdefault(self.key, []).append({"input": str(p), "output": None})
			idxs.append(len(LLM_TRACES[self.key]) - 1)
		self._pending[str(run_id)] = idxs
		try:
			self._starts[str(run_id)] = time.perf_counter()
		except Exception:
			pass

	def on_llm_end(self, response, run_id, parent_run_id=None, **kwargs):  # type: ignore[override]
		try:
			gens = response.generations  # list[list[Generation]]
			texts: List[str] = []
			for gen_list in gens:
				if not gen_list:
					texts.append("")
				else:
					# join multiple candidates if present
					out = "\n".join([getattr(g, "text", "") for g in gen_list])
					texts.append(out)
		except Exception:
			texts = ["<unavailable>"]
		idxs = self._pending.pop(str(run_id), [])
		# Map outputs by position; if sizes mismatch, pair best-effort
		for i, idx in enumerate(idxs):
			out = texts[i] if i < len(texts) else texts[-1] if texts else ""
			try:
				LLM_TRACES[self.key][idx]["output"] = out
			except Exception:
				pass
		try:
			start = self._starts.pop(str(run_id), None)
			if isinstance(start, (int, float)):
				elapsed = time.perf_counter() - float(start)
				LLM_DURATIONS.setdefault(self.key, []).append(float(elapsed))
		except Exception:
			pass


class ToolTrace(BaseModel):
	tool: str
	args: Optional[Any] = None
	output: str
	duration_secs: Optional[float] = None


class DomainResult(BaseModel):
	name: str
	intent: Optional[str] = None
	output: str
	traces: List[ToolTrace] = Field(default_factory=list)
	duration_secs: Optional[float] = None


class RouterTarget(BaseModel):
	extension: str
	intent: str


class RouterResult(BaseModel):
	targets: List[RouterTarget] = Field(default_factory=list)
	direct_text: Optional[str] = None


class Timing(BaseModel):
	name: str
	seconds: float


class AgentResult(BaseModel):
	final: str
	results: List[DomainResult] = Field(default_factory=list)
	timings: List[Timing] = Field(default_factory=list)
	# Minimal spec fields (for easy integrations)
	content: str
	response_time_secs: float
	traces: List[ToolTrace] = Field(default_factory=list)


def _wrap_callable_as_tool(fn: Callable[..., Any], ext_name: str):
	from langchain_core.tools import StructuredTool

	# Prefer full docstring so the domain agent sees complete instructions
	try:
		full_doc = inspect.getdoc(fn) or ""
	except Exception:
		full_doc = ""
	if full_doc.strip():
		description = full_doc.strip()
	else:
		# Fallback to summary + first example line
		meta = _doc_summary_and_example(fn)
		description = meta["summary"]
		if meta["example"]:
			description = f"{description} Example: {meta['example']}"

	sig = inspect.signature(fn)
	fields = {}
	# Resolve forward-ref annotations (e.g., Optional[str]) to actual types
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
		# Simple retry-on-exception once to handle transient/tool init errors
		last_err: Optional[str] = None
		for attempt in range(2):
			try:
				t0 = time.perf_counter()
				result = fn(**kwargs)
				# Prefer structured JSON for Pydantic or native containers
				if isinstance(result, BaseModel):
					try:
						sres = json.dumps(result.model_dump(), ensure_ascii=False)
					except Exception:
						# Try Pydantic v2 JSON, then v1 .json(), then str
						try:
							sres = result.model_dump_json()
						except Exception:
							try:
								sres = result.json()
							except Exception:
								sres = str(result)
				elif isinstance(result, (dict, list)):
					try:
						sres = json.dumps(result, ensure_ascii=False)
					except Exception:
						sres = str(result)
				else:
					sres = str(result)
				dur = time.perf_counter() - t0
				TOOL_TRACES.setdefault(ext_name, []).append({
					"tool": fn.__name__,
					"args": kwargs or None,
					"output": sres,
					"duration_secs": dur,
				})
				return sres
			except Exception as e:
				last_err = f"Error running tool {fn.__name__}: {str(e)}"
				# On first failure, try once more immediately
				if attempt == 0:
					continue
				try:
					dur = time.perf_counter() - t0  # type: ignore[name-defined]
				except Exception:
					dur = None
				TOOL_TRACES.setdefault(ext_name, []).append({
					"tool": fn.__name__,
					"args": kwargs or None,
					"output": last_err,
					"duration_secs": dur,
				})
				return last_err

	return StructuredTool(name=fn.__name__, description=description, args_schema=ArgsSchema, func=_runner)


def _wrap_extension_tools(ext: Dict[str, Any]):
	tools = []
	for fn in ext.get("tools", []):
		try:
			tools.append(_wrap_callable_as_tool(fn, ext.get("name", "unknown")))
		except Exception:
			continue
	return tools


def _build_light_schema(extensions: List[Dict[str, Any]]) -> str:
	parts: List[str] = []
	for ext in extensions:
		parts.append(build_light_schema_for_extension(ext))
	return "\n\n".join(p for p in parts if p)


def initialize_runtime(tool_root: Optional[str] = None) -> None:
	"""Preload extensions and the light schema into module-level caches.

	When tool_root is provided, only discover extensions under that root.
	"""
	global PRELOADED_EXTENSIONS, PRELOADED_SCHEMA, PRELOADED_TOOL_ROOT
	try:
		exts = discover_extensions(tool_root)
	except Exception:
		exts = []
	PRELOADED_EXTENSIONS = exts
	PRELOADED_SCHEMA = _build_light_schema(exts) if exts else ""
	PRELOADED_TOOL_ROOT = tool_root
	# Invalidate cached domain agents so they rebuild against the new extension set
	try:
		_build_domain_agent.cache_clear()  # type: ignore[attr-defined]
	except Exception:
		pass
	# Warm LLM clients (no callbacks so they are cached)
	try:
		_load_llm_for_role("router")
		_load_llm_for_role("domain")
		_load_llm_for_role("synth")
	except Exception:
		pass
	# Warm domain agents so first-turn overhead is minimized
	for ext in exts:
		name = ext.get("name")
		if not name:
			continue
		try:
			_build_domain_agent(name)
		except Exception:
			continue


def _get_extensions(tool_root: Optional[str] = None) -> List[Dict[str, Any]]:
	global PRELOADED_EXTENSIONS, PRELOADED_TOOL_ROOT
	if tool_root is not None:
		try:
			normalized_in = os.path.abspath(tool_root)
			normalized_pre = os.path.abspath(PRELOADED_TOOL_ROOT) if PRELOADED_TOOL_ROOT else None
		except Exception:
			normalized_in = tool_root
			normalized_pre = PRELOADED_TOOL_ROOT
		if normalized_in != normalized_pre:
			return discover_extensions(tool_root)
	return PRELOADED_EXTENSIONS if PRELOADED_EXTENSIONS is not None else discover_extensions(tool_root)


def _get_light_schema(extensions: List[Dict[str, Any]], tool_root: Optional[str] = None) -> str:
	global PRELOADED_EXTENSIONS, PRELOADED_SCHEMA, PRELOADED_TOOL_ROOT
	if PRELOADED_EXTENSIONS is not None and PRELOADED_SCHEMA is not None:
		try:
			pre = [e.get("name") for e in PRELOADED_EXTENSIONS]
			cur = [e.get("name") for e in extensions]
			same_exts = (pre == cur)
			if tool_root is None:
				same_root = (PRELOADED_TOOL_ROOT is None)
			else:
				try:
					same_root = os.path.abspath(PRELOADED_TOOL_ROOT or "") == os.path.abspath(tool_root)
				except Exception:
					same_root = (PRELOADED_TOOL_ROOT == tool_root)
			if same_exts and same_root:
				return PRELOADED_SCHEMA
		except Exception:
			pass
	return _build_light_schema(extensions)


async def _route(user_prompt: str, chat_history: Optional[str], memory: Optional[str], extensions: List[Dict[str, Any]], tool_root: Optional[str] = None) -> Tuple[RouterResult, float]:
	from langchain_core.messages import SystemMessage, HumanMessage

	llm = _load_llm_for_role("router")
	light_schema = _get_light_schema(extensions, tool_root=tool_root)
	ext_names = [ext["name"] for ext in extensions]

	system = (
		"You are a routing assistant. Given the Light Schema of available extensions, "
		"segment the user's request into per-extension intents. Do NOT select tools. "
		"Only return JSON with a 'targets' list. Each item has 'extension' and 'intent'. "
		"Only include extensions from the provided list."
		"Do not ask for claification about an intent that is going to a domain module. It can ask for itself"
		"ex: toggle my living room light and return my workout plan for to day -> home assisatnt(toggle living room light) , Coachbyte(return today's workout plan)"
        "If there is a generic prompt you dont have to use any of the extensions"
        "Generalbyte is not a catch all it is an extension do not use it for generic prompt just do use any extension for generic prompts or anything that doesnt require a tool from an extension"
		" Return JSON ONLY. If no extension is relevant, return {\"targets\": [] , \"direct_text\": \"<concise helpful reply>\" }. "
		" Do NOT include non-JSON text. Do NOT include 'direct_text' when 'targets' is non-empty."
	)
	messages = [
		SystemMessage(content=_with_date_prefix(system + "\n\nExtensions: " + ", ".join(ext_names) + "\n\nLight Schema:\n" + light_schema)),
		HumanMessage(content=f"User request: {user_prompt}\nChat history: {chat_history or ''}\nMemory: {memory or ''}\n\nReturn JSON only."),
	]

	# Measure only the LLM call duration for routing
	t_llm0 = time.perf_counter()
	structured = llm.with_structured_output(RouterResult)
	raw_obj = await structured.ainvoke(messages, config={"callbacks": [LLMRunTracer("router")]})
	router_llm_secs = time.perf_counter() - t_llm0
	try:
		router_obj = raw_obj if isinstance(raw_obj, RouterResult) else RouterResult.model_validate(raw_obj)
	except ValidationError:
		router_obj = RouterResult(targets=[], direct_text=None)

	targets = router_obj.targets
	# Filter to known extensions and normalize
	valid = []
	known = set(ext_names)
	for t in targets:
		ext_name = (t.extension or "").strip()
		intent = (t.intent or "").strip()
		if ext_name in known and intent:
			valid.append({"extension": ext_name, "intent": intent})
	# Fallback: if none, pick best guess by keyword match
	# Intentionally no fallback routing; if none are valid, return empty targets
	# Build validated RouterResult
	return RouterResult(targets=[RouterTarget(extension=v["extension"], intent=v["intent"]) for v in valid], direct_text=router_obj.direct_text), router_llm_secs


@lru_cache(maxsize=64)
def _build_domain_agent(ext_name: str) -> Any:
	from langgraph.prebuilt import create_react_agent

	# Reload extensions and find this one (cache key keeps cost small)
	exts = _get_extensions(PRELOADED_TOOL_ROOT)
	target = next((e for e in exts if e.get("name") == ext_name), None)
	if not target:
		raise RuntimeError(f"Unknown extension: {ext_name}")

	tools = _wrap_extension_tools(target)
	model = _load_llm_for_role("domain")
	# Prompt: prepend the extension's system prompt; create_react_agent accepts a 'prompt' argument
	agent = create_react_agent(model, tools=tools, prompt=_with_date_prefix(target.get("system_prompt", "")))
	return agent


async def _run_domain(ext_name: str, intent: str, latest_user_message: str, chat_history: Optional[str], memory: Optional[str]) -> DomainResult:
	from langchain_core.messages import HumanMessage, SystemMessage

	agent = _build_domain_agent(ext_name)
	try:
		# reset per-domain traces
		TOOL_TRACES[ext_name] = []
		LLM_DURATIONS[f"domain:{ext_name}"] = []
		messages = []
		if chat_history or memory:
			messages.append(SystemMessage(content=(
				"Conversation context to consider when responding.\n"
				f"Chat history:\n{chat_history or ''}\n\n"
				f"Memory:\n{memory or ''}"
			)))
		messages.append(HumanMessage(content=latest_user_message))
		messages.append(HumanMessage(content=f"Intent: {intent}"))
		result = await agent.ainvoke({"messages": messages}, config={"recursion_limit": 8, "callbacks": [LLMRunTracer(f"domain:{ext_name}")]})
		dur = float(sum(LLM_DURATIONS.get(f"domain:{ext_name}", []) or []))
		# result contains {"messages": [...]} ; take last message content
		messages = result.get("messages") if isinstance(result, dict) else None
		content = None
		if isinstance(messages, list) and messages:
			last = messages[-1]
			content = getattr(last, "content", None)
		if not isinstance(content, str):
			content = str(result)
		traces = [ToolTrace.model_validate(t) for t in (TOOL_TRACES.get(ext_name, []) or [])]
		return DomainResult(name=ext_name, intent=intent, output=content, traces=traces, duration_secs=dur)
	except Exception as e:
		traces = [ToolTrace.model_validate(t) for t in (TOOL_TRACES.get(ext_name, []) or [])]
		return DomainResult(name=ext_name, intent=intent, output=f"Error in {ext_name} agent: {str(e)}", traces=traces)


async def _synthesize(user_prompt: str, chat_history: Optional[str], memory: Optional[str], domain_results: List[DomainResult]) -> str:
	from langchain_core.messages import SystemMessage, HumanMessage

	llm = _load_llm_for_role("synth")
	system = (
		"You are a response synthesizer. Merge the domain outputs into a single, coherent, "
		"helpful reply. Resolve conflicts and be concise."
	)
	lines = [f"- {dr.name}: {dr.output}" for dr in domain_results]
	messages = [
		SystemMessage(content=_with_date_prefix(system)),
		HumanMessage(content=(
			f"User prompt: {user_prompt}\nChat history: {chat_history or ''}\nMemory: {memory or ''}\n"
			f"Domain results:\n" + "\n".join(lines)
		)),
	]
	resp = await llm.ainvoke(messages)
	return (resp.content or "").strip()


async def _respond_directly(user_prompt: str, chat_history: Optional[str], memory: Optional[str]) -> str:
	from langchain_core.messages import SystemMessage, HumanMessage

	llm = _load_llm_for_role("synth")
	system = (
		"You are a helpful assistant. The router found no relevant domain-specific extension for this request. "
		"Respond directly and helpfully to the user's message. Do not mention tools or extensions. Be concise."
	)
	messages = [SystemMessage(content=_with_date_prefix(system))]
	if chat_history or memory:
		messages.append(SystemMessage(content=(
			"Conversation context to consider when responding.\n"
			f"Chat history:\n{chat_history or ''}\n\n"
			f"Memory:\n{memory or ''}"
		)))
	messages.append(HumanMessage(content=user_prompt))
	resp = await llm.ainvoke(messages, config={"callbacks": [LLMRunTracer("direct")]})
	return (resp.content or "").strip()


async def run_agent(user_prompt: str, chat_history: Optional[str] = None, memory: Optional[str] = None, tool_root: Optional[str] = None) -> AgentResult:
	# Use preloaded extensions if available
	exts = _get_extensions(tool_root)
	if not exts:
		return AgentResult(
			final="No extensions discovered. Ensure files matching *_tool.py exist under extensions/.",
			results=[],
			timings=[],
			content="No extensions discovered. Ensure files matching *_tool.py exist under extensions/.",
			response_time_secs=0.0,
			traces=[],
		)

	# Router: segment intents (measure only LLM call duration inside _route)
	router_res, router_secs = await _route(user_prompt, chat_history, memory, exts, tool_root=tool_root)
	if not router_res.targets:
		# No targets — respond directly using router-provided direct_text if available
		if isinstance(router_res.direct_text, str) and router_res.direct_text.strip():
			final_direct = router_res.direct_text.strip()
			direct_secs = 0.0
		else:
			# Fallback to an LLM direct response if no text was extractable
			t_direct0 = time.perf_counter()
			final_direct = await _respond_directly(user_prompt, chat_history, memory)
			direct_secs = time.perf_counter() - t_direct0
		timings: List[Timing] = [Timing(name="router", seconds=router_secs), Timing(name="direct", seconds=direct_secs)]
		# Total time as sum of parts
		total_secs = sum(tm.seconds for tm in timings)
		timings.append(Timing(name="total", seconds=total_secs))
		# Minimal spec fields
		traces_flat: List[ToolTrace] = []
		return AgentResult(
			final=final_direct,
			results=[],
			timings=timings,
			content=final_direct,
			response_time_secs=total_secs,
			traces=traces_flat,
		)

	# Run domain agents in parallel
	tasks = [
		asyncio.create_task(_run_domain(t.extension, t.intent, user_prompt, chat_history, memory)) for t in router_res.targets
	]
	results: List[DomainResult] = []
	try:
		results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=float(_get_env("DOMAIN_TIMEOUT_SECS", "60") or 60))
	except asyncio.TimeoutError:
		for task, tgt in zip(tasks, router_res.targets):
			if not task.done():
				task.cancel()
				traces = [ToolTrace.model_validate(t) for t in (TOOL_TRACES.get(tgt.extension, []) or [])]
				results.append(DomainResult(name=tgt.extension, intent=tgt.intent, output="Timed out", traces=traces))
		# include completed ones
		for task in tasks:
			if task.done() and not task.cancelled():
				try:
					results.append(task.result())
				except Exception as e:
					results.append(DomainResult(name="unknown", intent=None, output=str(e), traces=[]))

	# Synthesizer: one-shot
	t_synth0 = time.perf_counter()
	final = await _synthesize(user_prompt, chat_history, memory, results)
	synth_secs = time.perf_counter() - t_synth0

	# Assemble timings
	timings: List[Timing] = [Timing(name="router", seconds=router_secs), Timing(name="synth", seconds=synth_secs)]
	for dr in results:
		if isinstance(dr.duration_secs, (int, float)):
			timings.append(Timing(name=f"domain:{dr.name}", seconds=float(dr.duration_secs)))
	# Total time as sum of parts (router + domains + synth)
	total_secs = sum(tm.seconds for tm in timings)
	timings.append(Timing(name="total", seconds=total_secs))

	# Minimal spec fields
	traces_flat: List[ToolTrace] = []
	for dr in results:
		for t in (dr.traces or []):
			try:
				traces_flat.append(ToolTrace.model_validate(t) if not isinstance(t, ToolTrace) else t)
			except Exception:
				pass
	return AgentResult(
		final=final,
		results=results,
		timings=timings,
		content=final,
		response_time_secs=total_secs,
		traces=traces_flat,
	)


def main(argv: List[str]) -> int:
	parser = argparse.ArgumentParser(description="Parallel Agent (Router + Domain Agents + Synthesizer)")
	parser.add_argument("-p", "--prompt", type=str, default="toggle the living room light.", help="Test prompt")
	parser.add_argument("-r", "--tool-root", type=str, default=None, help="Optional root directory to discover tools under")
	args = parser.parse_args(argv)

	# Allow blocking run for Windows PowerShell simplicity
	models = _active_models()
	print(f"Active models: router={models.get('router')} | domain={models.get('domain')} | synth={models.get('synth')}")
	print("")
	# Preload extensions/schema to reduce setup latency
	try:
		initialize_runtime(tool_root=args.tool_root)
	except Exception:
		pass
	try:
		ret = asyncio.run(run_agent(args.prompt, tool_root=args.tool_root))
	except RuntimeError:
		# In case of existing running loop (e.g., notebooks)
		loop = asyncio.get_event_loop()
		ret = loop.run_until_complete(run_agent(args.prompt, tool_root=args.tool_root))
	# Print minimal debug: intent per domain and tool traces, then final output
	if isinstance(ret, AgentResult):
		results = ret.results or []
		report_lines: List[str] = []
		for dr in results:
			traces = dr.traces or []
			report_lines.append(f"Domain: {dr.name}")
			if dr.intent:
				report_lines.append(f"Intent: {dr.intent}")
			if dr.duration_secs is not None:
				report_lines.append(f"Duration: {dr.duration_secs:.2f}s")
			for t in traces:
				report_lines.append(f"- {t.tool}")
				args_str = json.dumps(t.args, ensure_ascii=False)
				report_lines.append(f"  args: {args_str}")
				report_lines.append(f"  output: {t.output}")
			report_lines.append("")
		if report_lines:
			print("\n".join(report_lines).strip())
			print("\n---\n")
		print(ret.final)
		# Print timings summary
		if ret.timings:
			print("\nTimings:")
			for tm in ret.timings:
				print(f"- {tm.name}: {tm.seconds:.2f}s")
	else:
		print(str(ret))
	return 0


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))


