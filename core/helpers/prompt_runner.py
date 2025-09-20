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

    active_agent_rel = os.getenv("ACTIVE_AGENT_PATH", "core/agent/parallel_agent.py")
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
    for prompt in prompts:
        proc = subprocess.run(
            [sys.executable, str(agent_path), "-p", str(prompt), "-r", str(tool_root_path)],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=float(env.get("PROMPT_RUNNER_STEP_TIMEOUT_SECS", "120") or 120),
            env=env,
        )
        if proc.returncode != 0:
            # Bubble up failure on first error
            return proc.returncode
    return 0


def main(argv: List[str]) -> int:
    # When used as a CLI: args are prompts; run them in order
    return run_prompts(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))





