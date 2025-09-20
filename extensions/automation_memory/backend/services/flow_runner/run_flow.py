import os
import sys
import json
from pathlib import Path

def main(argv):
    if len(argv) < 2:
        print("usage: run_flow.py <call_name> <json_prompts>")
        return 1
    call_name = argv[0]
    try:
        prompts = json.loads(argv[1])
    except Exception:
        print("invalid prompts json")
        return 1
    active_agent = os.getenv('ACTIVE_AGENT_PATH', 'core/agent/parallel_agent.py')
    repo_root = Path(__file__).resolve().parents[5]
    agent_path = (repo_root / active_agent).resolve()
    if not agent_path.exists():
        print(f"[runner] agent not found at {agent_path}")
        return 1
    # Use the shared prompt runner helper to handle session memory
    sys.path.insert(0, str(repo_root))
    from core.helpers.prompt_runner import run_prompts  # type: ignore
    code = run_prompts([str(p) for p in (prompts or [])], tool_root='extensions')
    if code != 0:
        sys.stderr.write(f"[runner] flow failed with code {code}\n")
        return code
    print("completed")
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))


