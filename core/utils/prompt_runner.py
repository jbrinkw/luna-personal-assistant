"""Prompt runner utility for Luna.

Executes a series of prompts using a specified agent, maintaining session context.
Ported from legacy code with minimal changes.
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional


def _repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).resolve().parents[2]


def run_prompts(prompts: List[str], agent_path: Optional[str] = None, tool_root: Optional[str] = None) -> int:
    """Run a series of prompts using the specified agent.
    
    Args:
        prompts: List of prompt strings to execute
        agent_path: Path to agent module (relative to repo root or absolute)
        tool_root: Optional tool discovery root (defaults to extensions/)
        
    Returns:
        Exit code (0 for success)
    """
    if not isinstance(prompts, list) or not all(isinstance(p, str) for p in prompts):
        raise ValueError("prompts must be a list of strings")
    
    # Determine agent path
    if agent_path is None:
        agent_path = os.getenv('ACTIVE_AGENT_PATH', 'core/agents/simple_agent/agent.py')
    
    repo = _repo_root()
    agent_full_path = (repo / agent_path).resolve()
    
    if not agent_full_path.exists():
        raise FileNotFoundError(f"Agent not found: {agent_full_path}")
    
    # Tool discovery root defaults to extensions/
    tool_root_path = (repo / (tool_root or "extensions")).resolve()
    
    # Prepare environment
    env = os.environ.copy()
    try:
        existing = env.get("PYTHONPATH", "")
        sep = os.pathsep if existing else ""
        env["PYTHONPATH"] = f"{existing}{sep}{str(repo)}"
    except Exception:
        pass
    
    total = len(prompts)
    for idx, prompt in enumerate(prompts, start=1):
        try:
            proc = subprocess.run(
                [sys.executable, str(agent_full_path), "-p", prompt, "-r", str(tool_root_path)],
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=float(env.get("PROMPT_RUNNER_STEP_TIMEOUT_SECS", "120") or 120),
                env=env,
            )
            
            # Echo outputs for observability
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
        
        except subprocess.TimeoutExpired:
            sys.stderr.write(f"[prompt_runner] step {idx}/{total} timed out\n")
            return 1
        except Exception as e:
            sys.stderr.write(f"[prompt_runner] step {idx}/{total} error: {e}\n")
            return 1
    
    return 0


def main(argv: List[str]) -> int:
    """CLI entry point - args are prompts to run in order."""
    if not argv:
        print("Usage: prompt_runner.py <prompt1> [prompt2 ...]")
        return 1
    
    return run_prompts(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

