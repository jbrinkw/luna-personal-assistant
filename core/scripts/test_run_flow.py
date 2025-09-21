#!/usr/bin/env python3
"""
End-to-end test for the Task Flow run pipeline.

It exercises three layers:
  1) Agent direct: runs core/agent/hierarchical.py once per prompt
  2) Runner direct: runs extensions/.../run_flow.py with prompts JSON
  3) API (UI path): calls /api/task_flows to ensure flow exists, then POST /run

Usage examples:
  python core/scripts/test_run_flow.py \
    --call-name "play spotify on my tv" \
    --prompts "press the home button on the tv" "open spotify on the tv" "press the play button on the tv"

Environment:
  AM_API_PORT: backend API port (default 3051)
  PYTHON_BIN:  interpreter for direct runner (defaults to current interpreter)
  ACTIVE_AGENT_PATH: overrides agent path (default core/agent/hierarchical.py)
  PYTHONPATH: repo root is appended automatically for subprocesses
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple
import asyncio


REPO_ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
if str(REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(REPO_ROOT))
try:
    from dotenv import load_dotenv as _load_dotenv  # type: ignore
    _load_dotenv()
    _load_dotenv(dotenv_path=str(REPO_ROOT / '.env'))
except Exception:
    pass
DEFAULT_CALL_NAME = "play spotify on my tv"
DEFAULT_PROMPTS = [
    "press the home button on the tv",
    "open spotify on the tv",
    "press the play button on the tv",
]


def _env_with_repo() -> dict:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    sep = os.pathsep if existing else ""
    env["PYTHONPATH"] = f"{existing}{sep}{str(REPO_ROOT)}"
    return env


def run_agent_direct(prompts: List[str]) -> Tuple[int, str, str]:
    """Run the agent directly once per prompt, as prompt_runner does."""
    agent_rel = os.getenv("ACTIVE_AGENT_PATH", "core/agent/hierarchical.py")
    agent_path = (REPO_ROOT / agent_rel).resolve()
    if not agent_path.exists():
        return 1, "", f"Agent not found: {agent_path}"
    tool_root = (REPO_ROOT / "extensions").resolve()
    stdout_all: List[str] = []
    stderr_all: List[str] = []
    for p in prompts:
        proc = subprocess.run(
            [sys.executable, str(agent_path), "-p", str(p), "-r", str(tool_root)],
            cwd=str(REPO_ROOT),
            env=_env_with_repo(),
            capture_output=True,
            text=True,
            timeout=float(os.getenv("PROMPT_RUNNER_STEP_TIMEOUT_SECS", "120") or 120),
        )
        stdout_all.append(proc.stdout or "")
        stderr_all.append(proc.stderr or "")
        if proc.returncode != 0:
            return proc.returncode, "\n".join(stdout_all).strip(), "\n".join(stderr_all).strip()
    return 0, "\n".join(stdout_all).strip(), "\n".join(stderr_all).strip()


def run_agent_direct_steps(prompts: List[str]) -> List[Tuple[str, int, str, str]]:
    """Run the agent once per prompt and return per-step outputs.

    Returns a list of tuples: (prompt, return_code, stdout, stderr)
    """
    agent_rel = os.getenv("ACTIVE_AGENT_PATH", "core/agent/hierarchical.py")
    agent_path = (REPO_ROOT / agent_rel).resolve()
    if not agent_path.exists():
        return [("", 1, "", f"Agent not found: {agent_path}")]
    tool_root = (REPO_ROOT / "extensions").resolve()
    results: List[Tuple[str, int, str, str]] = []
    for p in prompts:
        proc = subprocess.run(
            [sys.executable, str(agent_path), "-p", str(p), "-r", str(tool_root)],
            cwd=str(REPO_ROOT),
            env=_env_with_repo(),
            capture_output=True,
            text=True,
            timeout=float(os.getenv("PROMPT_RUNNER_STEP_TIMEOUT_SECS", "120") or 120),
        )
        results.append((p, int(proc.returncode), (proc.stdout or ""), (proc.stderr or "")))
        if proc.returncode != 0:
            # Stop at first failure to reflect real runner behavior
            break
    return results


async def run_agent_inproc_steps(prompts: List[str]) -> List[Tuple[str, int, str, List[dict]]]:
    """Run the agent in-process for each prompt, preserving session context.

    Returns list of (prompt, return_code, final_text, traces)
    traces is a list of {tool, args, output, duration_secs}
    """
    try:
        # Lazy import to keep script light when not used
        from core.agent import simple_passthough as agent_mod
    except Exception as e:
        return [("", 1, f"import agent failed: {e}", [])]

    # Initialize tools once
    try:
        agent_mod.initialize_runtime(tool_root=str(REPO_ROOT / "extensions"))
    except Exception:
        pass

    results: List[Tuple[str, int, str, List[dict]]] = []
    chat_history = ""  # accumulate simple user/assistant lines if needed later
    for p in prompts:
        try:
            res = await agent_mod.run_agent(p, chat_history=chat_history or None, memory=None, tool_root=str(REPO_ROOT / "extensions"))
            final_text = str(getattr(res, "final", "") or getattr(res, "content", "") or "")
            traces_out: List[dict] = []
            try:
                for t in getattr(res, "traces", []) or []:
                    traces_out.append({
                        "tool": getattr(t, "tool", None),
                        "args": getattr(t, "args", None),
                        "output": getattr(t, "output", None),
                        "duration_secs": getattr(t, "duration_secs", None),
                    })
            except Exception:
                pass
            results.append((p, 0, final_text, traces_out))
            # Optionally accumulate minimal history (user: last prompt; assistant: final)
            if final_text:
                chat_history = (chat_history + ("\n" if chat_history else "") + f"user: {p}\nassistant: {final_text}")
            else:
                chat_history = (chat_history + ("\n" if chat_history else "") + f"user: {p}")
        except Exception as e:
            results.append((p, 1, f"agent error: {e}", []))
            break
    return results


def run_runner_direct(call_name: str, prompts: List[str]) -> Tuple[int, str, str]:
    """Run the Python flow runner script directly (bypasses Node API)."""
    runner = REPO_ROOT / "extensions" / "automation_memory" / "backend" / "services" / "flow_runner" / "run_flow.py"
    if not runner.exists():
        return 1, "", f"Runner not found: {runner}"
    py = os.getenv("PYTHON_BIN") or sys.executable
    proc = subprocess.run(
        [py, str(runner), str(call_name), json.dumps(prompts)],
        cwd=str(REPO_ROOT),
        env=_env_with_repo(),
        capture_output=True,
        text=True,
        timeout=float(os.getenv("PROMPT_RUNNER_TOTAL_TIMEOUT_SECS", "600") or 600),
    )
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def _api_base() -> str:
    base = os.getenv("AM_API_BASE")
    if base and base.strip():
        return base.strip()
    port = os.getenv("AM_API_PORT", "3051")
    return f"http://localhost:{port}"


def _http_json(method: str, path: str, data: Optional[dict] = None, timeout: float = 30.0):
    url = _api_base().rstrip("/") + path
    body = None
    headers = {"Content-Type": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = (resp.read() or b"").decode("utf-8", errors="replace")
            try:
                return resp.getcode(), json.loads(text)
            except Exception:
                return resp.getcode(), {"_raw": text}
    except urllib.error.HTTPError as e:
        try:
            text = (e.read() or b"").decode("utf-8", errors="replace")
        except Exception:
            text = ""
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, {"error": text or str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def ensure_flow(call_name: str, prompts: List[str]) -> Optional[int]:
    code, data = _http_json("GET", "/api/task_flows")
    if code != 200:
        print(f"[api] list flows failed: {code} {data}")
        return None
    flow = None
    for item in (data or []):
        if isinstance(item, dict) and str(item.get("call_name") or "").strip().lower() == call_name.strip().lower():
            flow = item
            break
    if flow is None:
        code, data = _http_json("POST", "/api/task_flows", {"call_name": call_name, "prompts": prompts})
        if code != 200 or not isinstance(data, dict) or not data.get("id"):
            print(f"[api] create flow failed: {code} {data}")
            return None
        flow_id = int(data["id"])  # type: ignore[arg-type]
        print(f"[api] created flow id={flow_id}")
        return flow_id
    try:
        fid = int(flow.get("id"))  # type: ignore[arg-type]
    except Exception:
        print(f"[api] invalid flow object: {flow}")
        return None
    # Keep prompts in sync if needed (best-effort)
    if list(flow.get("prompts") or []) != list(prompts or []):
        _http_json("PUT", f"/api/task_flows/{fid}", {"prompts": prompts})
    return fid


def run_via_api(flow_id: int) -> Tuple[int, dict]:
    code, data = _http_json("POST", f"/api/task_flows/{flow_id}/run", {})
    return code, (data if isinstance(data, dict) else {"_raw": data})


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="E2E test for Task Flow pipeline")
    p.add_argument("--call-name", type=str, default=DEFAULT_CALL_NAME)
    p.add_argument("--prompts", type=str, nargs="*", default=DEFAULT_PROMPTS)
    p.add_argument("--skip-agent", action="store_true", help="Skip direct agent step")
    p.add_argument("--skip-runner", action="store_true", help="Skip direct runner step")
    p.add_argument("--skip-api", action="store_true", help="Skip API step")
    args = p.parse_args(argv)

    call_name = args.call_name
    prompts = [str(s) for s in (args.prompts or []) if isinstance(s, str) and s.strip()]
    if not prompts:
        prompts = DEFAULT_PROMPTS

    print("\n=== Config ===")
    print(f"repo:        {REPO_ROOT}")
    print(f"call_name:   {call_name}")
    print(f"prompts:     {json.dumps(prompts, ensure_ascii=False)}")
    print(f"api_base:    {_api_base()}")
    print(f"python:      {os.getenv('PYTHON_BIN') or sys.executable}")
    print(f"agent_path:  {os.getenv('ACTIVE_AGENT_PATH', 'core/agent/hierarchical.py')}")

    agent_stdout_combined: Optional[str] = None
    if not args.skip_agent:
        print("\n--- Step 1: Agent in-process (stepwise, with traces) ---")
        step_results_inproc = asyncio.run(run_agent_inproc_steps(prompts))
        all_ok = True
        outs: List[str] = []
        for idx, (pp, rc, final_text, traces) in enumerate(step_results_inproc, start=1):
            print(f"[step {idx}/{len(prompts)}] prompt: {pp!r}")
            print(f"return code: {rc}")
            if final_text:
                print("[final]\n" + final_text)
                outs.append(final_text)
            if traces:
                print("[traces]")
                try:
                    print(json.dumps(traces, ensure_ascii=False, indent=2))
                except Exception:
                    print(str(traces))
            if rc != 0:
                all_ok = False
                print("[result] Agent step FAILED; stopping early.")
                break
            else:
                print("[result] Agent step OK.")
        agent_stdout_combined = ("\n".join([o for o in outs if o]).strip() or None) if outs else None
        if not all_ok:
            return 1

        print("\n--- Step 1b: Agent direct (subprocess, for comparison) ---")
        step_results = run_agent_direct_steps(prompts)
        all_ok = True
        outs: List[str] = []
        for idx, (pp, rc, out, err) in enumerate(step_results, start=1):
            print(f"[step {idx}/{len(prompts)}] prompt: {pp!r}")
            print(f"return code: {rc}")
            if out:
                print("[stdout]\n" + out)
                outs.append(out)
            if err:
                print("[stderr]\n" + err)
            if rc != 0:
                all_ok = False
                print("[result] Agent step FAILED; stopping early.")
                break
            else:
                print("[result] Agent step OK.")
        agent_stdout_combined = ("\n".join([o for o in outs if o]).strip() or None) if outs else None
        if not all_ok:
            return 1

    if not args.skip_runner:
        print("\n--- Step 2: Runner direct ---")
        rc, out, err = run_runner_direct(call_name, prompts)
        print(f"return code: {rc}")
        if out:
            print("[stdout]\n" + out)
        if err:
            print("[stderr]\n" + err)
        if rc != 0:
            print("[result] Runner direct FAILED; stopping early.")
            return rc
        else:
            print("[result] Runner direct OK.")

    if not args.skip_api:
        print("\n--- Step 3: API (UI path) ---")
        fid = ensure_flow(call_name, prompts)
        if fid is None:
            print("[result] API ensure flow FAILED.")
            return 2
        print(f"Running flow id={fid} via API...")
        code, data = run_via_api(fid)
        print(f"HTTP: {code}")
        print("Response:")
        try:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            print(str(data))
        if code != 200 or not data or not data.get("ok"):
            print("[result] API run FAILED.")
            return 3
        print("[result] API run OK.")

    # Always return/show the agent's output if we have it
    if agent_stdout_combined:
        print("\n=== Agent Output ===")
        print(agent_stdout_combined)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())





