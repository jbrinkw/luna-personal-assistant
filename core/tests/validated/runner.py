import os
import sys
import json
import subprocess
from typing import Any, Dict, List, Tuple, Optional

try:
	from dotenv import load_dotenv  # type: ignore
	load_dotenv()
except Exception:
	pass


# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)


def _run_one(agent_path: str, tool_root: str, prompt: str) -> Dict[str, Any]:
	"""Invoke the common single-run adapter to get the final text.

	Returns a dict with at least: {"final": str}.
	"""
	cmd = [
		sys.executable,
		"-m",
		"core.tests.facade._single_run",
		"--agent",
		agent_path,
		"--tool-root",
		tool_root,
		"--prompt",
		prompt,
	]
	try:
		env = os.environ.copy()
		# Ensure repo root is importable in the child process
		prev_pp = env.get("PYTHONPATH", "")
		if REPO_ROOT not in prev_pp.split(":" ):
			env["PYTHONPATH"] = (REPO_ROOT + (":" + prev_pp if prev_pp else ""))
		proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=env)
		out = (proc.stdout or "").strip()
		err = (proc.stderr or "").strip()
		payload = json.loads(out) if out else {}
		if err:
			payload["stderr"] = err
		payload.setdefault("final", "")
		payload.setdefault("called_tools", [])
		return payload
	except Exception as e:
		return {"final": f"<runner error: {e}>", "called_tools": [], "stderr": None}


def _judge_pair(expected: str, actual: str, *, model_name: str, called_tools: Optional[List[str]] = None, tool_traces: Optional[Any] = None) -> str:
	"""Call the LLM to judge whether actual matches expected.

	Returns "pass" or "fail".
	"""
	from core.helpers.llm_selector import get_chat_model
	from langchain_core.messages import SystemMessage, HumanMessage

	sys_msg = (
		"You are a pragmatic test judge. Decide if ACTUAL sufficiently satisfies EXPECTED.\n"
		"Accept paraphrases, different wording, and formatting differences.\n"
		"JSON: ignore key order, whitespace, quotes, and extra benign fields.\n"
		"Numbers: treat '135' == '135.0'; allow small numeric deviations (e.g., time remaining within ~±90s).\n"
		"Summaries: if EXPECTED is 'summary updated', accept 'Summary updated: <text>'.\n"
		"Plans/lists: ordering differences are acceptable if items match overall intent.\n"
		"Timer/status: accept approximate phrasing conveying the same state.\n"
		"Tool traces may be provided: if they show the operation succeeded with content consistent with EXPECTED, mark PASS even if ACTUAL text is paraphrased.\n"
		"Default to PASS when meaning clearly matches; FAIL only when meaning conflicts or is missing.\n"
		"Respond with exactly one token: PASS or FAIL."
	)
	# Build user message with context (truncate traces to keep prompt small)
	traces_text = ""
	if tool_traces:
		try:
			traces_text = json.dumps(tool_traces, ensure_ascii=False)
			if len(traces_text) > 4000:
				traces_text = traces_text[:4000] + "..."
		except Exception:
			traces_text = str(tool_traces)
	ct_text = ", ".join(called_tools or [])
	user_msg = (
		f"EXPECTED:\n{expected}\n\n"
		f"ACTUAL:\n{actual}\n\n"
		f"CALLED_TOOLS:\n{ct_text}\n\n"
		f"TOOL_TRACES:\n{traces_text}\n\n"
		"Answer strictly with PASS or FAIL."
	)

	try:
		model = get_chat_model(role="synth", model=model_name, callbacks=[], temperature=0.0)
		resp = model.invoke([SystemMessage(content=sys_msg), HumanMessage(content=user_msg)])
		text = (getattr(resp, "content", None) or str(resp) or "").strip().upper()
		if "PASS" in text and "FAIL" not in text:
			return "pass"
		if text == "PASS":
			return "pass"
		return "fail"
	except Exception:
		# Conservative on error
		return "fail"


def run_tests(agent_path: str, tool_root: str, tests: List[Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
	"""Run prompts in parallel (multiprocessing) and judge via a fast LLM.

	Environment overrides:
	- TESTS_AGENT_PATH: overrides agent_path
	- TESTS_TOOL_ROOT: overrides tool_root
	- TESTS_JUDGE_MODEL: overrides the LLM judge model (default: gpt-4.1-mini)

	Returns a dict: {"passed": int, "failed": int, "results": ["pass"|"fail", ...]}.
	"""
	# Env overrides for convenience
	agent_path = os.getenv("TESTS_AGENT_PATH", agent_path)
	tool_root = os.getenv("TESTS_TOOL_ROOT", tool_root)
	# Normalize to absolute paths for subprocess stability
	if isinstance(agent_path, str) and agent_path and not os.path.isabs(agent_path):
		agent_path = os.path.join(REPO_ROOT, agent_path)
	if isinstance(tool_root, str) and tool_root and not os.path.isabs(tool_root):
		tool_root = os.path.join(REPO_ROOT, tool_root)
	judge_model = os.getenv("TESTS_JUDGE_MODEL", "gpt-4.1-mini")

	# First, run all prompts in parallel processes
	from concurrent.futures import ProcessPoolExecutor, as_completed

	prompts: List[str] = [str(t.get("prompt", "")) for t in tests]
	results_json: List[Dict[str, Any]] = [{} for _ in tests]
	with ProcessPoolExecutor(max_workers=min(8, max(1, len(prompts)))) as pool:
		future_map = {pool.submit(_run_one, agent_path, tool_root, p): idx for idx, p in enumerate(prompts)}
		for fut in as_completed(future_map):
			idx = future_map[fut]
			try:
				results_json[idx] = fut.result()
			except Exception as e:
				results_json[idx] = {"final": f"<runner error: {e}>", "called_tools": []}

	# Print raw outputs and detailed per-test debugging, and judge each test
	judgments: List[str] = []
	for idx, (test, rj) in enumerate(zip(tests, results_json), start=1):
		prompt = str(test.get("prompt", ""))
		expected = str(test.get("expected") or test.get("expected_response") or "")
		actual = str(rj.get("final", ""))
		called = rj.get("called_tools", [])
		stderr = rj.get("stderr")
		traces = rj.get("tool_traces")
		errors = rj.get("errors")
		print(f"[raw output {idx}]\n{actual}\n")
		print(f"[test {idx}] Prompt: {prompt}")
		print(f"[test {idx}] Expected: {expected}")
		print(f"[test {idx}] Actual: {actual}")
		print(f"[test {idx}] Called tools: {called}")
		if isinstance(stderr, str) and stderr.strip():
			print(f"[test {idx}] STDERR: {stderr}")
		if traces:
			try:
				print(f"[test {idx}] Tool traces: {json.dumps(traces, ensure_ascii=False)[:2000]}")
			except Exception:
				print(f"[test {idx}] Tool traces: <unprintable>")
		if errors:
			try:
				print(f"[test {idx}] Errors: {json.dumps(errors, ensure_ascii=False)}")
			except Exception:
				print(f"[test {idx}] Errors: <unprintable>")
		verdict = _judge_pair(expected, actual, model_name=judge_model)
		print(f"[test {idx}] Judge: {verdict}")
		judgments.append(verdict)

	passed = sum(1 for r in judgments if r == "pass")
	failed = sum(1 for r in judgments if r == "fail")
	print(f"[validated] {tool_name} — Pass/fail: {passed}/{failed}")
	print(f"Results: {judgments}")
	return {"passed": passed, "failed": failed, "results": list(judgments)}


__all__ = ["run_tests"]


