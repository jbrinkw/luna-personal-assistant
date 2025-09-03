import importlib.util
import inspect
import os
from typing import Dict, List, Tuple, Callable


def _load_module_from_path(label: str, path: str):
    spec = importlib.util.spec_from_file_location(label, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {label} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def _clean_desc(desc: str | None) -> str:
    if not desc:
        return ""
    return " ".join(str(desc).split())


def _classify_group(tool_short_name: str) -> str:
    name = tool_short_name.strip().upper()
    if name.startswith("UPDATE"):
        return "Update tools"
    if name.startswith("GET"):
        return "Getter tools"
    if name.startswith("ACTION"):
        return "Actions tools"
    return "Other tools"


def _collect_functions(module, prefix: str) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if not name.upper().startswith(prefix.upper() + "_"):
            continue
        short = name[len(prefix) + 1 :]
        doc = _clean_desc((inspect.getdoc(obj) or "").strip())
        out.append((name, short, doc))
    return out


def _collect_all_functions(module) -> List[Tuple[str, str]]:
    """Collect all top-level functions as (name, doc)."""
    out: List[Tuple[str, str]] = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        doc = _clean_desc((inspect.getdoc(obj) or "").strip())
        out.append((name, doc))
    return out


def _classify_ui_tool(name: str) -> str:
    """Group UI tool functions into Update/Getter/Actions buckets by name."""
    n = name.lower().strip()
    if n.startswith("get"):
        return "Getter tools"
    if n.startswith("update") or n.startswith("new"):
        return "Update tools"
    if n.startswith("set") or n.startswith("log") or n.startswith("complete"):
        return "Actions tools"
    return "Other tools"


def _find_repo_root(start_dir: str) -> str:
    """Walk upwards from start_dir to find a directory that contains both 'extensions' and 'core'.

    Falls back to the computed 3-levels-up path if no match is found.
    """
    current = os.path.abspath(start_dir)
    fallback = os.path.abspath(os.path.join(start_dir, "..", "..", ".."))
    while True:
        if os.path.isdir(os.path.join(current, "extensions")) and os.path.isdir(os.path.join(current, "core")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            # reached filesystem root
            return os.path.abspath(fallback)
        current = parent


def build_light_schema_text() -> str:
    """Build a compact human-readable light schema from local tool files.

    Domains included: GeneralByte, HomeAssistant.
    """
    repo_root = _find_repo_root(os.path.dirname(__file__))

    # GeneralByte
    gb_path = os.path.join(repo_root, "extensions", "generalbyte", "code", "tool_local.py")
    gb_lines: List[str] = ["GeneralByte"]
    try:
        gb_mod = _load_module_from_path("gb_local_tools", gb_path)
        funcs = _collect_functions(gb_mod, "GENERAL")
        grouped: Dict[str, List[Tuple[str, str, str]]] = {
            "Update tools": [],
            "Getter tools": [],
            "Actions tools": [],
            "Other tools": [],
        }
        for full, short, desc in funcs:
            grp = _classify_group(short)
            grouped[grp].append((full, short, desc))
        for grp_label in grouped:
            grouped[grp_label].sort(key=lambda x: x[1].lower())
        for grp_label in ("Update tools", "Getter tools", "Actions tools"):
            gb_lines.append(grp_label)
            if grouped[grp_label]:
                for full, _short, desc in grouped[grp_label]:
                    gb_lines.append(f"- {full}: {desc}" if desc else f"- {full}:")
            gb_lines.append("")
        if grouped["Other tools"]:
            gb_lines.append("Other tools")
            for full, _short, desc in grouped["Other tools"]:
                gb_lines.append(f"- {full}: {desc}" if desc else f"- {full}:")
            gb_lines.append("")
    except Exception as exc:
        gb_lines.extend(["Update tools", "Getter tools", "Actions tools", f"- error: {exc}", ""])  # fallback

    # HomeAssistant
    ha_path = os.path.join(repo_root, "core", "integrations", "homeassistant_local_tools.py")
    ha_lines: List[str] = ["HomeAssistant"]
    try:
        ha_mod = _load_module_from_path("ha_local_tools", ha_path)
        funcs = _collect_functions(ha_mod, "HA")
        grouped: Dict[str, List[Tuple[str, str, str]]] = {
            "Update tools": [],
            "Getter tools": [],
            "Actions tools": [],
            "Other tools": [],
        }
        for full, short, desc in funcs:
            grp = _classify_group(short)
            grouped[grp].append((full, short, desc))
        for grp_label in grouped:
            grouped[grp_label].sort(key=lambda x: x[1].lower())
        for grp_label in ("Update tools", "Getter tools", "Actions tools"):
            ha_lines.append(grp_label)
            if grouped[grp_label]:
                for full, short, desc in grouped[grp_label]:
                    if full in ("HA_GET_entity_status", "HA_ACTION_turn_entity_on", "HA_ACTION_turn_entity_off"):
                        # Emphasize that these accept friendly names or entity IDs
                        suffix = " Accepts friendly name or entity_id." if desc else "Accepts friendly name or entity_id."
                        label = f"- {full}: {desc}{suffix}" if desc else f"- {full}: {suffix}"
                        ha_lines.append(label)
                    else:
                        ha_lines.append(f"- {full}: {desc}" if desc else f"- {full}:")
            ha_lines.append("")
        if grouped["Other tools"]:
            ha_lines.append("Other tools")
            for full, _short, desc in grouped["Other tools"]:
                ha_lines.append(f"- {full}: {desc}" if desc else f"- {full}:")
            ha_lines.append("")
    except Exception as exc:
        ha_lines.extend(["Update tools", "Getter tools", "Actions tools", f"- error: {exc}", ""])  # fallback

    # ChefByte
    chef_path = os.path.join(repo_root, "extensions", "chefbyte", "code", "local_tools.py")
    chef_lines: List[str] = ["ChefByte"]
    try:
        chef_mod = _load_module_from_path("chef_local_tools", chef_path)
        funcs = _collect_functions(chef_mod, "CHEF")
        grouped: Dict[str, List[Tuple[str, str, str]]] = {
            "Update tools": [],
            "Getter tools": [],
            "Actions tools": [],
            "Other tools": [],
        }
        for full, short, desc in funcs:
            grp = _classify_group(short)
            grouped[grp].append((full, short, desc))
        for grp_label in grouped:
            grouped[grp_label].sort(key=lambda x: x[1].lower())
        for grp_label in ("Update tools", "Getter tools", "Actions tools"):
            chef_lines.append(grp_label)
            if grouped[grp_label]:
                for full, _short, desc in grouped[grp_label]:
                    chef_lines.append(f"- {full}: {desc}" if desc else f"- {full}:")
            chef_lines.append("")
        if grouped["Other tools"]:
            chef_lines.append("Other tools")
            for full, _short, desc in grouped["Other tools"]:
                chef_lines.append(f"- {full}: {desc}" if desc else f"- {full}:")
            chef_lines.append("")
    except Exception as exc:
        chef_lines.extend(["Update tools", "Getter tools", "Actions tools", f"- error: {exc}", ""])  # fallback

    # CoachByte (use UI tools so names match prompts like 'new_daily_plan')
    coach_ui_path = os.path.join(repo_root, "extensions", "coachbyte", "ui", "tools", "__init__.py")
    coach_lines: List[str] = ["CoachByte"]
    try:
        coach_ui_mod = _load_module_from_path("coach_ui_tools", coach_ui_path)
        funcs_ui = _collect_all_functions(coach_ui_mod)
        grouped_ui: Dict[str, List[Tuple[str, str]]] = {
            "Update tools": [],
            "Getter tools": [],
            "Actions tools": [],
            "Other tools": [],
        }
        for fname, fdoc in funcs_ui:
            grp = _classify_ui_tool(fname)
            grouped_ui[grp].append((fname, fdoc))
        for grp_label in grouped_ui:
            grouped_ui[grp_label].sort(key=lambda x: x[0].lower())
        for grp_label in ("Update tools", "Getter tools", "Actions tools"):
            coach_lines.append(grp_label)
            if grouped_ui[grp_label]:
                for fname, fdoc in grouped_ui[grp_label]:
                    coach_lines.append(f"- {fname}: {fdoc}" if fdoc else f"- {fname}:")
            coach_lines.append("")
        if grouped_ui["Other tools"]:
            coach_lines.append("Other tools")
            for fname, fdoc in grouped_ui["Other tools"]:
                coach_lines.append(f"- {fname}: {fdoc}" if fdoc else f"- {fname}:")
            coach_lines.append("")
    except Exception as exc:
        coach_lines.extend(["Update tools", "Getter tools", "Actions tools", f"- error: {exc}", ""])  # fallback

    lines: List[str] = []
    lines.extend(gb_lines)
    lines.extend(ha_lines)
    lines.extend(chef_lines)
    lines.extend(coach_lines)
    return "\n".join(lines).rstrip() + "\n"


