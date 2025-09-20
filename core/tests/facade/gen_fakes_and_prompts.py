import os
import sys
import inspect
from typing import Any, Dict, List


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)


EXT_DIR = os.path.join(PROJECT_ROOT, "extensions")
FAKES_DIR = os.path.join(PROJECT_ROOT, "core", "tests", "fakes")
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "core", "tests", "test_prompts")


def _read_doc_lines(fn) -> List[str]:
	doc = inspect.getdoc(fn) or ""
	return doc.splitlines()


def _extract_second_and_third_lines(fn) -> Dict[str, str]:
	lines = _read_doc_lines(fn)
	if len(lines) < 3:
		raise RuntimeError(f"Docstring for {fn.__name__} must have at least 3 lines (summary, example prompt, Example Response)")
	second = lines[1].strip()
	third = lines[2].strip()
	if not second:
		raise RuntimeError(f"Missing example prompt (second line) for {fn.__name__}")
	if not third.lower().startswith("example response:"):
		raise RuntimeError(f"Third line must start with 'Example Response:' for {fn.__name__}")
	resp = third.split(":", 1)[1].strip()
	if not resp:
		raise RuntimeError(f"Empty Example Response for {fn.__name__}")
	return {"prompt": second, "response": resp}


def _import_ext_module(path: str):
	import importlib.util
	name = os.path.splitext(os.path.basename(path))[0]
	spec = importlib.util.spec_from_file_location(name, path)
	mod = importlib.util.module_from_spec(spec)
	assert spec and spec.loader
	spec.loader.exec_module(mod)  # type: ignore[attr-defined]
	return mod


def _ensure_dir(p: str):
	os.makedirs(p, exist_ok=True)


HEADER = '"""Auto-generated fake tools for tests. DO NOT EDIT BY HAND."""\n\nfrom __future__ import annotations\n\nfrom typing import Any, Dict, List, Optional\n\n\n'


def _generate_fake_module(ext_name: str, real_mod, out_path: str):
	name_line = f"NAME = \"{ext_name}\"\n\n"
	sys_prompt_val = getattr(real_mod, "SYSTEM_PROMPT", "")
	sys_prompt_safe = (sys_prompt_val or "").replace('"""', '\\"\\"\\"')
	sp_line = f"SYSTEM_PROMPT = \"\"\"{sys_prompt_safe}\"\"\"\n\n"
	tools = getattr(real_mod, "TOOLS", [])
	if not tools:
		raise RuntimeError(f"No TOOLS found in {real_mod.__name__}")
	lines: List[str] = [HEADER, name_line, sp_line]
	fn_defs: List[str] = []
	tool_refs: List[str] = []
	for fn in tools:
		meta = _extract_second_and_third_lines(fn)
		sig = inspect.signature(fn)
		params = ", ".join(str(p) for p in sig.parameters.values())
		ret_ann = ""  # keep implicit return for simplicity
		# Reuse full docstring to mirror real tool docs
		doc = inspect.getdoc(fn) or ""
		body = f"\n\ndef {fn.__name__}({params}){ret_ann}:\n\t\"\"\"{doc}\n\t\"\"\"\n\treturn {repr(meta['response'])}\n"
		fn_defs.append(body)
		tool_refs.append(fn.__name__)
	lines.extend(fn_defs)
	lines.append("\n\nTOOLS = [\n\t" + ",\n\t".join(tool_refs) + "\n]\n")
	with open(out_path, "w", encoding="utf-8") as f:
		f.write("".join(lines))


def _generate_prompts_module(ext_name: str, real_mod, out_path: str):
	tools = getattr(real_mod, "TOOLS", [])
	tests: List[Dict[str, Any]] = []
	for fn in tools:
		meta = _extract_second_and_third_lines(fn)
		tests.append({"prompt": meta["prompt"], "expected_tool": fn.__name__})
	content = (
		"import sys\nimport os\n\nPROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))\nif PROJECT_ROOT not in sys.path:\n\tsys.path.insert(0, PROJECT_ROOT)\n\nTESTS = "
		+ repr(tests)
		+ f"\nTOOL_NAME = \"{ext_name}\"\nDEFAULT_TOOL_ROOT = os.getenv(\"TESTS_TOOL_ROOT\", \"core/tests/fakes\")\nDEFAULT_AGENT_PATH = os.getenv(\"TESTS_AGENT_PATH\", \"core/agent/hierarchical.py\")\n\nif __name__ == \"__main__\":\n\tfrom core.tests.runner import run_tests\n\trun_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)\n"
	)
	with open(out_path, "w", encoding="utf-8") as f:
		f.write(content)


def main(argv: List[str]) -> int:
	# Walk extensions and generate fakes/prompts for each *_tool.py
	for root, _, files in os.walk(EXT_DIR):
		for fname in files:
			if not fname.endswith("_tool.py"):
				continue
			real_path = os.path.join(root, fname)
			real_mod = _import_ext_module(real_path)
			ext_name = getattr(real_mod, "NAME", os.path.splitext(fname)[0])
			group = os.path.basename(os.path.dirname(real_path))
			fake_dir = os.path.join(FAKES_DIR, group)
			prompts_path = os.path.join(PROMPTS_DIR, f"{group}_tools.py")
			_ensure_dir(fake_dir)
			_ensure_dir(PROMPTS_DIR)
			_generate_fake_module(ext_name=ext_name, real_mod=real_mod, out_path=os.path.join(fake_dir, fname))
			_generate_prompts_module(ext_name=ext_name, real_mod=real_mod, out_path=prompts_path)
	print("Generation complete.")
	return 0


if __name__ == "__main__":
	import sys as _sys
	raise SystemExit(main(_sys.argv[1:]))


