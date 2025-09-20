"""AutomationMemory — run named task flows.

Static tool exposing a single function to run a flow by call_name.
System prompt enumerates available flows dynamically from the backend.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List
import subprocess

NAME = "AutomationMemory"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _api_base() -> str:
    # Local backend default
    return f"http://localhost:{os.getenv('AM_API_PORT','3051')}"


def _list_flows() -> List[str]:
    try:
        import urllib.request
        with urllib.request.urlopen(_api_base() + "/api/task_flows", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        names = [str(item.get("call_name") or "").strip() for item in (data or [])]
        return [n for n in names if n]
    except Exception:
        return []


def _system_prompt() -> str:
    flows = _list_flows()
    if flows:
        lines = "\n".join(f"- {n}" for n in flows)
        return (
            "Run named task flows. Each flow is a list of prompts executed sequentially "
            "via the active agent. Only report completion.\n\n"
            f"Available flows (call names):\n{lines}"
        )
    return (
        "Run named task flows. Each flow is a list of prompts executed sequentially "
        "via the active agent. Only report completion. No flows are currently defined."
    )


SYSTEM_PROMPT = _system_prompt()


def RUN_flow(call_name: str) -> str:
    """Run a named task flow by its call name.
    Example Prompt: run the flow play spotify on my tv
    Example Args: {"call_name": "play spotify on my tv"}
    """
    try:
        # Resolve prompts from backend
        import urllib.request
        with urllib.request.urlopen(_api_base() + "/api/task_flows", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        target = None
        for item in data or []:
            if str(item.get("call_name") or "").strip().lower() == call_name.strip().lower():
                target = item
                break
        if not target:
            return "no prompts found for flow"
        # Call backend run endpoint to execute with active agent
        req = urllib.request.Request(
            _api_base() + f"/api/task_flows/{target.get('id')}/run",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=60) as resp2:
            _ = resp2.read()
        return "completed"
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


TOOLS = [
    RUN_flow,
]


# Dynamically augment the tool docstring with the current list of flows so
# the tooltip/help text always reflects what's available.
def _update_tool_doc() -> None:
    try:
        flows = _list_flows()
    except Exception:
        flows = []
    base = (
        "Run a named task flow by its call name.\n\n"
        "Example Prompt: run the flow play spotify on my tv\n"
        "Example Args: {\"call_name\": \"play spotify on my tv\"}"
    )
    if flows:
        lines = "\n".join(f"- {n}" for n in flows)
        base = base + "\n\nAvailable flows (call names):\n" + lines
    try:
        RUN_flow.__doc__ = base
    except Exception:
        pass


# Apply on module import
_update_tool_doc()




