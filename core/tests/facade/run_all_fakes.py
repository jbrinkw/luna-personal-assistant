import os
import sys
import importlib
import subprocess
import re
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


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
	modules = _discover_prompt_modules()
	if not modules:
		print("No test prompt modules found.")
		return 1

	def _run_module(modname: str) -> Tuple[str, int, int, int]:
		name = modname.rsplit(".", 1)[-1]
		path = os.path.join(PROMPTS_DIR, f"{name}.py")
		cmd = [sys.executable, path]
		try:
			proc = subprocess.run(cmd, capture_output=True, text=True)
			out = proc.stdout.strip()
		except Exception as e:
			out = f"<runner error: {e}>"
		passed = partial = failed = 0
		m = re.search(r"Pass/partial/fail:\s*(\d+)/(\d+)/(\d+)", out)
		if m:
			try:
				passed = int(m.group(1))
				partial = int(m.group(2))
				failed = int(m.group(3))
			except Exception:
				passed = partial = failed = 0
		return out, passed, partial, failed

	overall_passed = 0
	overall_partial = 0
	overall_failed = 0

	results_by_module: Dict[str, Tuple[str, int, int, int]] = {}
	with ThreadPoolExecutor(max_workers=min(8, max(1, len(modules)))) as pool:
		future_map = {pool.submit(_run_module, modname): modname for modname in modules}
		for fut in as_completed(future_map):
			modname = future_map[fut]
			try:
				out, p, pr, f = fut.result()
			except Exception as e:
				out, p, pr, f = (f"<runner error: {e}>", 0, 0, 0)
			results_by_module[modname] = (out, p, pr, f)

	for modname in modules:
		out, p, pr, f = results_by_module.get(modname, ("", 0, 0, 0))
		print(f"\n=== Running {modname} ===")
		if out:
			print(out)
		overall_passed += p
		overall_partial += pr
		overall_failed += f

	print("\n=== Summary (all fakes) ===")
	print(f"Pass/partial/fail: {overall_passed}/{overall_partial}/{overall_failed}")
	return 0 if overall_failed == 0 else 2


if __name__ == "__main__":
	import sys as _sys
	raise SystemExit(main(_sys.argv[1:]))


