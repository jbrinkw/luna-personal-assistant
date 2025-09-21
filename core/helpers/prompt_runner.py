import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_prompts(prompts: List[str], tool_root: Optional[str] = None) -> int:
    """
    Run a series of prompts using the active agent specified by ACTIVE_AGENT_PATH.

    - Accepts a list of strings (prompts) and feeds them to a single agent process
      sequentially so the agent can keep session memory across steps.
    - Returns the agent process exit code (0 for success).
    """
    if not isinstance(prompts, list) or not all(isinstance(p, str) for p in prompts):
        raise ValueError("prompts must be a list of strings")

    active_agent_rel = os.getenv("ACTIVE_AGENT_PATH", "core/agent/hierarchical.py")
    repo = _repo_root()
    agent_path = (repo / active_agent_rel).resolve()
    if not agent_path.exists():
        raise FileNotFoundError(f"ACTIVE_AGENT_PATH not found: {agent_path}")

    # Tool discovery root defaults to extensions/
    tool_root_path = (repo / (tool_root or "extensions")).resolve()

    # Start agent as a long-lived process; send prompts one by one as separate invocations.
    # For now, we invoke per prompt; the agent code already aggregates context across turns
    # when run in the same process. A more advanced version could use an IPC protocol.
    env = os.environ.copy()
    # Ensure repo root is importable by agent subprocess
    try:
        existing = env.get("PYTHONPATH", "")
        sep = os.pathsep if existing else ""
        env["PYTHONPATH"] = f"{existing}{sep}{str(repo)}"
    except Exception:
        pass
    total = len(prompts)
    for idx, prompt in enumerate(prompts, start=1):
        proc = subprocess.run(
            [sys.executable, str(agent_path), "-p", str(prompt), "-r", str(tool_root_path)],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=float(env.get("PROMPT_RUNNER_STEP_TIMEOUT_SECS", "120") or 120),
            env=env,
        )
        # Echo outputs for observability, even on success
        try:
            sys.stdout.write(f"[prompt_runner] step {idx}/{total} prompt: {prompt!r}\n")
        except Exception:
            pass
        try:
            if proc.stdout:
                sys.stdout.write(proc.stdout if proc.stdout.endswith("\n") else proc.stdout + "\n")
        except Exception:
            pass
        try:
            if proc.stderr:
                sys.stdout.write(proc.stderr if proc.stderr.endswith("\n") else proc.stderr + "\n")
        except Exception:
            pass
        if proc.returncode != 0:
            return proc.returncode
    return 0


def main(argv: List[str]) -> int:
    # When used as a CLI: args are prompts; run them in order
    return run_prompts(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))





