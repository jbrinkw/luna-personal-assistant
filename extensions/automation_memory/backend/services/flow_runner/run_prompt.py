import os
import sys
import json
import subprocess
from pathlib import Path

def main(argv):
    if len(argv) < 1:
        print("usage: run_prompt.py <prompt>")
        return 1
    prompt = argv[0]
    active_agent = os.getenv('ACTIVE_AGENT_PATH', 'core/agent/parallel_agent.py')
    # Ensure absolute path for repo root
    repo_root = Path(__file__).resolve().parents[5]
    agent_path = (repo_root / active_agent).resolve()
    if not agent_path.exists():
        print(f"[runner] agent not found at {agent_path}")
        return 1
    env = os.environ.copy()
    # Discover tools under extensions/ by default
    tool_root = str((repo_root / 'extensions').resolve())
    try:
        proc = subprocess.run([
            sys.executable,
            str(agent_path),
            '-p', prompt,
            '-r', tool_root,
        ], cwd=str(repo_root), capture_output=True, text=True, timeout=120, env=env)
        if proc.returncode == 0:
            sys.stdout.write(proc.stdout)
            return 0
        else:
            sys.stderr.write(proc.stderr)
            return proc.returncode
    except Exception as e:
        print(f"[runner] error: {e}")
        return 1

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))





