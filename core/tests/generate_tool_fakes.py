"""Generate fake tool modules for testing.

This script scans the `extensions/` directory for `*_tool.py` modules and
creates lightweight, side‑effect‑free "fake" copies under `core/tests/fakes/`
that preserve:
- NAME
- SYSTEM_PROMPT (if present)
- TOOLS list membership
- Function names, argument signatures, and docstrings

The generated functions contain no operational code and simply return None.

Usage:
  python -m core.tests.generate_tool_fakes
  # or
  python core/tests/generate_tool_fakes.py
"""

from __future__ import annotations

import os
import sys
import ast
from typing import List, Tuple, Optional


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
EXTENSIONS_DIR = os.path.join(PROJECT_ROOT, "extensions")
OUTPUT_BASE = os.path.join(os.path.dirname(__file__), "fakes")


def _ensure_sys_path() -> None:
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _unparse(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    try:
        # Python 3.9+
        return ast.unparse(node)
    except Exception:
        return None


def _extract_constant_string(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    try:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # repr() preserves quotes suitable for code emission
            return repr(node.value)
        # Fall back to unparse for multi-part strings
        up = _unparse(node)
        if isinstance(up, str):
            return up
    except Exception:
        pass
    return None


def _gather_tools_list(node: ast.AST) -> List[str]:
    names: List[str] = []
    if isinstance(node, (ast.List, ast.Tuple)):
        for elt in node.elts:
            if isinstance(elt, ast.Name):
                names.append(elt.id)
            elif isinstance(elt, ast.Attribute):
                # Best effort: take attribute name, though our tools are bare names in this repo
                names.append(elt.attr)
    return names


def _format_param(name: str, annotation: Optional[str], default: Optional[str], is_vararg: bool, is_kwarg: bool) -> str:
    prefix = "*" if is_vararg else ("**" if is_kwarg else "")
    parts: List[str] = [f"{prefix}{name}"]
    if annotation:
        parts[-1] += f": {annotation}"
    if default is not None:
        parts[-1] += f" = {default}"
    return parts[0]


def _build_signature(fn: ast.FunctionDef) -> str:
    args = fn.args
    pieces: List[str] = []

    # posonly + normal positional args
    posonly = list(getattr(args, "posonlyargs", []) or [])
    positional = list(args.args or [])
    ordered = posonly + positional

    defaults = list(args.defaults or [])
    num_required = len(ordered) - len(defaults)

    for idx, a in enumerate(ordered):
        ann = _unparse(a.annotation)
        default = None
        if idx >= num_required:
            default = _unparse(defaults[idx - num_required])
        pieces.append(_format_param(a.arg, ann, default, False, False))

    # vararg
    if args.vararg is not None:
        ann = _unparse(args.vararg.annotation)
        pieces.append(_format_param(args.vararg.arg, ann, None, True, False))

    # kwonly args
    if args.kwonlyargs:
        if args.vararg is None:
            # bare star to indicate keyword-only section
            pieces.append("*")
        for idx, ka in enumerate(args.kwonlyargs):
            ann = _unparse(ka.annotation)
            dflt_node = args.kw_defaults[idx] if idx < len(args.kw_defaults) else None
            default = _unparse(dflt_node) if dflt_node is not None else None
            pieces.append(_format_param(ka.arg, ann, default, False, False))

    # kwarg
    if args.kwarg is not None:
        ann = _unparse(args.kwarg.annotation)
        pieces.append(_format_param(args.kwarg.arg, ann, None, False, True))

    return ", ".join(pieces)


def _build_return_annotation(fn: ast.FunctionDef) -> str:
    ret = _unparse(fn.returns)
    return f" -> {ret}" if ret else ""


def _collect_module_info(source_path: str) -> Tuple[Optional[str], Optional[str], List[str], dict[str, ast.FunctionDef]]:
    """Return (NAME_literal, SYSTEM_PROMPT_literal, tool_function_names, function_defs_by_name)."""
    src = _read_text(source_path)
    tree = ast.parse(src, filename=source_path)

    name_literal: Optional[str] = None
    system_prompt_literal: Optional[str] = None
    tool_names: List[str] = []
    fn_defs: dict[str, ast.FunctionDef] = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "NAME":
                    name_literal = _extract_constant_string(node.value)
                if isinstance(target, ast.Name) and target.id == "SYSTEM_PROMPT":
                    system_prompt_literal = _extract_constant_string(node.value)
                if isinstance(target, ast.Name) and target.id == "TOOLS":
                    tool_names = _gather_tools_list(node.value)
        elif isinstance(node, ast.FunctionDef):
            fn_defs[node.name] = node

    # Fallback if TOOLS not found: collect all top-level functions that look like tool functions
    if not tool_names:
        for name in fn_defs:
            if name.isupper() or name.startswith("COACHBYTE_") or name.startswith("GENERAL_") or name.startswith("HA_"):
                tool_names.append(name)

    return name_literal, system_prompt_literal, tool_names, fn_defs


def _emit_stub_module(
    *,
    name_literal: Optional[str],
    system_prompt_literal: Optional[str],
    tool_names: List[str],
    fn_defs: dict[str, ast.FunctionDef],
    module_name: str,
) -> str:
    lines: List[str] = []
    lines.append('"""Auto-generated fake tool module. Do not edit by hand.\n\nThis module mirrors function names, signatures, and docstrings from the\noriginal tool, but contains no operational code. All functions return None.\n"""')
    lines.append("from __future__ import annotations")
    lines.append("")
    if name_literal:
        lines.append(f"NAME = {name_literal}")
    if system_prompt_literal:
        lines.append(f"SYSTEM_PROMPT = {system_prompt_literal}")
    if name_literal or system_prompt_literal:
        lines.append("")

    # Emit stub functions for each tool in TOOLS
    emitted: List[str] = []
    for fn_name in tool_names:
        node = fn_defs.get(fn_name)
        if node is None:
            # Skip unknown names
            continue
        sig = _build_signature(node)
        ret_ann = _build_return_annotation(node)
        doc = ast.get_docstring(node, clean=False) or ""
        # Ensure we always emit a docstring block
        doc_literal = repr(doc)
        lines.append(f"def {fn_name}({sig}){ret_ann}:")
        lines.append(f"    \"\"\"{doc}\"\"\"") if "\n" in doc else lines.append(f"    {doc_literal}")
        # body: explicitly return None (do nothing)
        lines.append("    return None")
        lines.append("")
        emitted.append(fn_name)

    # Tools list
    if emitted:
        joined = ", ".join(emitted)
        lines.append("TOOLS = [" + joined + "]")
        lines.append("")
        lines.append("__all__ = ['NAME', 'SYSTEM_PROMPT', 'TOOLS', " + ", ".join([repr(n) for n in emitted]) + "]")

    return "\n".join(lines) + "\n"


def _relative_to_extensions(path: str) -> str:
    return os.path.relpath(path, EXTENSIONS_DIR)


def _destination_for(source_file: str) -> str:
    rel = _relative_to_extensions(source_file)
    # Place under fakes/ with the same subdirectory structure and filename
    return os.path.join(OUTPUT_BASE, rel)


def _ensure_inits(path: str) -> None:
    # Ensure packages exist with __init__.py from OUTPUT_BASE down to file dir
    base = OUTPUT_BASE
    rel_dir = os.path.dirname(os.path.relpath(path, OUTPUT_BASE))
    current = base
    if rel_dir and rel_dir != ".":
        for part in rel_dir.split(os.sep):
            current = os.path.join(current, part)
            os.makedirs(current, exist_ok=True)
            init_path = os.path.join(current, "__init__.py")
            if not os.path.exists(init_path):
                _write_text(init_path, "")


def _find_tool_modules() -> List[str]:
    res: List[str] = []
    if not os.path.isdir(EXTENSIONS_DIR):
        return res
    for root, _dirs, files in os.walk(EXTENSIONS_DIR):
        for fn in files:
            if fn.endswith("_tool.py"):
                res.append(os.path.join(root, fn))
    return res


def generate() -> List[Tuple[str, str]]:
    """Generate all stubs. Returns list of (source, destination)."""
    _ensure_sys_path()
    results: List[Tuple[str, str]] = []
    for src in _find_tool_modules():
        name_literal, system_prompt_literal, tool_names, fn_defs = _collect_module_info(src)
        module_name = os.path.splitext(os.path.basename(src))[0]
        out_code = _emit_stub_module(
            name_literal=name_literal,
            system_prompt_literal=system_prompt_literal,
            tool_names=tool_names,
            fn_defs=fn_defs,
            module_name=module_name,
        )
        dest = _destination_for(src)
        _ensure_inits(dest)
        _write_text(dest, out_code)
        results.append((src, dest))
    # Ensure base __init__.py exists
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    base_init = os.path.join(OUTPUT_BASE, "__init__.py")
    if not os.path.exists(base_init):
        _write_text(base_init, "")
    return results


def main(argv: List[str]) -> int:
    results = generate()
    print(f"Generated {len(results)} fake tool module(s):")
    for src, dst in results:
        rel_src = os.path.relpath(src, PROJECT_ROOT)
        rel_dst = os.path.relpath(dst, PROJECT_ROOT)
        print(f"- {rel_src} -> {rel_dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


