import os
import sys
import importlib.util
import inspect
import textwrap
from types import ModuleType
from typing import List, Dict, Any


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
EXTENSIONS_DIR = os.path.join(PROJECT_ROOT, "extensions")


def _import_module_from_path(path: str) -> ModuleType:
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _parse_tool_doc(fn) -> Dict[str, str]:
    doc = inspect.getdoc(fn) or ""
    raw_lines = doc.splitlines()
    lines = [ln.rstrip() for ln in raw_lines]
    summary = lines[0].strip() if lines else ""
    # find first non-empty line after summary as example (robust to blank lines)
    example = ""
    example_idx = None
    for idx in range(1, len(lines)):
        candidate = lines[idx].strip()
        if candidate:
            example = candidate
            example_idx = idx
            break
    # notes are everything after the example line
    notes_start = (example_idx + 1) if example_idx is not None else 1
    notes = "\n".join(lines[notes_start:]).strip() if len(lines) > notes_start else ""
    return {"summary": summary, "example": example, "notes": notes}


def discover_extensions() -> List[Dict[str, Any]]:
    exts: List[Dict[str, Any]] = []
    if not os.path.isdir(EXTENSIONS_DIR):
        return exts
    for root, dirs, files in os.walk(EXTENSIONS_DIR):
        for fname in files:
            if not fname.endswith("_tool.py"):
                continue
            path = os.path.join(root, fname)
            mod = _import_module_from_path(path)
            # Require NAME, SYSTEM_PROMPT, TOOLS
            name = getattr(mod, "NAME", None)
            system_prompt = getattr(mod, "SYSTEM_PROMPT", None)
            tools = getattr(mod, "TOOLS", None)
            if not isinstance(name, str) or not isinstance(system_prompt, str) or not isinstance(tools, list):
                continue
            callable_tools = [t for t in tools if callable(t)]
            exts.append({
                "name": name.strip(),
                "system_prompt": system_prompt.strip(),
                "tools": callable_tools,
                "module_path": path,
            })
    return exts


def build_light_schema_for_extension(ext: Dict[str, Any]) -> str:
    system_prompt = ext.get("system_prompt", "")
    name = ext.get("name", "")
    first_line = system_prompt.splitlines()[0].strip() if system_prompt else ""
    lines: List[str] = []
    if first_line:
        lines.append(f"{name} — {first_line}")
    else:
        lines.append(f"{name}")
    for fn in ext.get("tools", []):
        meta = _parse_tool_doc(fn)
        tool_name = fn.__name__
        entry = f"- {tool_name}: {meta['summary']}"
        if meta["example"]:
            entry += f" EX: \"{meta['example']}\""
        lines.append(entry)
    return "\n".join(lines)


def build_all_light_schema() -> str:
    exts = discover_extensions()
    sections = [build_light_schema_for_extension(ext) for ext in exts]
    return "\n\n".join([s for s in sections if s])


def main(argv: List[str]) -> int:
    # ensure project root on sys.path so relative imports work if needed
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    schema = build_all_light_schema()
    print(schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


