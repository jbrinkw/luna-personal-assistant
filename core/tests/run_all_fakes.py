import os
import sys
import importlib
from typing import Any, Dict, List


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)


PROMPTS_DIR = os.path.join(PROJECT_ROOT, "core", "tests", "test_prompts")


def _discover_prompt_modules() -> List[str]:
	mods: List[str] = []
	for fname in os.listdir(PROMPTS_DIR):
		if not fname.endswith("_tools.py"):
			continue
		name = os.path.splitext(fname)[0]
		mods.append(f"core.tests.test_prompts.{name}")
	return sorted(mods)


def main(argv: List[str]) -> int:
	from core.tests.runner import run_tests

	modules = _discover_prompt_modules()
	if not modules:
		print("No test prompt modules found.")
		return 1

	overall_passed = 0
	overall_partial = 0
	overall_failed = 0

	for modname in modules:
		mod = importlib.import_module(modname)
		TESTS = getattr(mod, "TESTS", [])
		TOOL_NAME = getattr(mod, "TOOL_NAME", os.path.basename(modname))
		DEFAULT_TOOL_ROOT = getattr(mod, "DEFAULT_TOOL_ROOT", "core/tests/fakes")
		DEFAULT_AGENT_PATH = getattr(mod, "DEFAULT_AGENT_PATH", "core/agent/parallel_agent.py")
		print(f"\n=== Running {modname} ===")
		result: Dict[str, Any] = run_tests(
			agent_path=DEFAULT_AGENT_PATH,
			tool_root=DEFAULT_TOOL_ROOT,
			tests=TESTS,
			tool_name=TOOL_NAME,
		)
		overall_passed += int(result.get("passed", 0))
		overall_partial += int(result.get("partial", 0))
		overall_failed += int(result.get("failed", 0))

	print("\n=== Summary (all fakes) ===")
	print(f"Pass/partial/fail: {overall_passed}/{overall_partial}/{overall_failed}")
	return 0 if overall_failed == 0 else 2


if __name__ == "__main__":
	import sys as _sys
	raise SystemExit(main(_sys.argv[1:]))


