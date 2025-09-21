import os
import sys
import json
import asyncio
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
    active_agent = os.getenv('ACTIVE_AGENT_PATH', 'core/agent/hierarchical.py')
    repo_root = Path(__file__).resolve().parents[5]
    # Load repo .env so tools (e.g., Home Assistant) have credentials in this process and children
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=str(repo_root / '.env'))
    except Exception:
        pass
    agent_path = (repo_root / active_agent).resolve()
    if not agent_path.exists():
        print(f"[runner] agent not found at {agent_path}")
        return 1
    # Ensure repo on path and import agent to run in-process (like the test script)
    sys.path.insert(0, str(repo_root))
    # Debug header
    try:
        print(f"[runner.py] call={call_name} steps={len(prompts or [])} agent={agent_path}")
        print(f"[runner.py] HA_URL={'set' if os.getenv('HA_URL') else 'unset'} HA_TOKEN={'set' if os.getenv('HA_TOKEN') else 'unset'} REMOTE={os.getenv('HA_REMOTE_ENTITY_ID') or '(default)'}")
    except Exception:
        pass

    try:
        from core.agent import simple_passthough as agent_mod  # type: ignore
    except Exception as e:
        sys.stderr.write(f"[runner] import agent failed: {e}\n")
        return 1

    # Initialize tools once
    try:
        agent_mod.initialize_runtime(tool_root=str(repo_root / 'extensions'))
    except Exception:
        pass

    async def _run_one(prompt: str, chat_history: str) -> tuple[int, str, list]:
        try:
            res = await agent_mod.run_agent(prompt, chat_history=(chat_history or None), memory=None, tool_root=str(repo_root / 'extensions'))
            final_text = str(getattr(res, 'final', '') or getattr(res, 'content', '') or '')
            traces_out = []
            try:
                for t in getattr(res, 'traces', []) or []:
                    traces_out.append({
                        'tool': getattr(t, 'tool', None),
                        'args': getattr(t, 'args', None),
                        'output': getattr(t, 'output', None),
                        'duration_secs': getattr(t, 'duration_secs', None),
                    })
            except Exception:
                pass
            return 0, final_text, traces_out
        except Exception as e:
            return 1, f"agent error: {e}", []

    chat_history = ''
    total = len(prompts or [])
    for idx, p in enumerate([str(x) for x in (prompts or [])], start=1):
        print(f"[runner.step] {idx}/{total} prompt: {p!r}")
        rc, final_text, traces = asyncio.run(_run_one(p, chat_history))
        if final_text:
            print("[final]\n" + final_text)
        if traces:
            try:
                print("[traces]\n" + json.dumps(traces, ensure_ascii=False))
            except Exception:
                print("[traces] (unjsonable)")
        if final_text:
            chat_history = (chat_history + ("\n" if chat_history else "") + f"user: {p}\nassistant: {final_text}")
        else:
            chat_history = (chat_history + ("\n" if chat_history else "") + f"user: {p}")
        if rc != 0:
            sys.stderr.write(f"[runner] step failed at {idx} with code {rc}\n")
            return rc

    print("completed")
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))


