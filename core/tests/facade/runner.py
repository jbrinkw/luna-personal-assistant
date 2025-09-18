import asyncio
import importlib.util
import os
import sys
import subprocess
import json
from types import ModuleType
try:
	from dotenv import load_dotenv  # type: ignore
	load_dotenv()
except Exception:
	pass
try:
	from dotenv import load_dotenv  # type: ignore
	load_dotenv()
except Exception:
	pass
from typing import Any, Dict, List


def _import_module_from_path(path: str) -> ModuleType:
	name = os.path.splitext(os.path.basename(path))[0]
	spec = importlib.util.spec_from_file_location(name, path)
	mod = importlib.util.module_from_spec(spec)
	assert spec and spec.loader
	spec.loader.exec_module(mod)  # type: ignore[attr-defined]
	return mod


async def _invoke_agent(agent_mod: ModuleType, prompt: str, tool_root: str):
	"""Invoke the agent's async run function and return (result_obj, final_text)."""
	try:
		res = await agent_mod.run_agent(prompt, tool_root=tool_root)
		final = getattr(res, "final", None)
		final_text = final if isinstance(final, str) else str(res)
		return res, final_text
	except Exception as e:
		return None, f"<agent error: {e}>"


def _tool_names_from_result(res_obj) -> List[str]:
	try:
		results = getattr(res_obj, "results", []) or []
		names: List[str] = []
		for dr in results:
			traces = getattr(dr, "traces", []) or []
			for t in traces:
				name = getattr(t, "tool", None)
				if isinstance(name, str) and name:
					names.append(name)
		return names
	except Exception:
		return []


def run_tests(agent_path: str, tool_root: str, tests: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
	"""Run prompts concurrently against the agent and judge by tool traces.

	Returns a dict: {"passed": int, "partial": int, "failed": int, "results": ["pass"|"partial"|"fail", ...]}.
	"""
	# Env overrides for convenience
	agent_path = os.getenv("TESTS_AGENT_PATH", agent_path)
	tool_root = os.getenv("TESTS_TOOL_ROOT", tool_root)
	# Ensure project root is on sys.path
	project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
	if project_root not in sys.path:
		sys.path.insert(0, project_root)

	def _run_one(prompt: str) -> Dict[str, Any]:
		cmd = [
			sys.executable,
			"-m",
			"core.tests._single_run",
			"--agent",
			agent_path,
			"--tool-root",
			tool_root,
			"--prompt",
			prompt,
		]
		proc = subprocess.run(cmd, capture_output=True, text=True)
		out = proc.stdout.strip()
		try:
			return json.loads(out) if out else {"final": "", "called_tools": []}
		except Exception:
			return {"final": out, "called_tools": []}

	def _run_all():
		from concurrent.futures import ThreadPoolExecutor
		outputs: List[str] = []
		judgments: List[str] = []
		with ThreadPoolExecutor(max_workers=min(8, max(1, len(tests)))) as pool:
			futs = [pool.submit(_run_one, t.get("prompt", "")) for t in tests]
			results_json = [f.result() for f in futs]
		for idx, (test, rj) in enumerate(zip(tests, results_json), start=1):
			final = rj.get("final", "")
			called = rj.get("called_tools", [])
			outputs.append(final)
			print(f"[raw output {idx}]\n{final}\n")
			expected = test.get("expected_tool")
			if isinstance(expected, str) and expected:
				if called == [expected]:
					judgments.append("pass")
				elif expected in called and len(called) > 1:
					judgments.append("partial")
				else:
					judgments.append("fail")
			else:
				judgments.append("fail")
			print(f"[tools {idx}] expected={expected} called={called}")
		return outputs, judgments

	outputs, results = _run_all()

	passed = sum(1 for r in results if r == "pass")
	partial = sum(1 for r in results if r == "partial")
	failed = sum(1 for r in results if r == "fail")
	print(f"Pass/partial/fail: {passed}/{partial}/{failed}")
	print(f"Results: {results}")
	return {"passed": passed, "partial": partial, "failed": failed, "results": list(results)}


