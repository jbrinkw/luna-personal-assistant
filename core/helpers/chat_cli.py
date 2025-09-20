import os
import sys
import json
import asyncio
import argparse
import time
from typing import List, Optional

# Ensure project root on sys.path for absolute imports when running as a script
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

# Resolve active agent module from env path (defaults to hierarchical)
ACTIVE_AGENT_PATH = os.getenv("ACTIVE_AGENT_PATH", "core/agent/hierarchical.py")

def _import_agent_from_path(path: str):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, os.path.join(PROJECT_ROOT, path))
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod
    except Exception:
        # Fallback to built-in hierarchical agent
        from core.agent import hierarchical as fallback

        return fallback

pa = _import_agent_from_path(ACTIVE_AGENT_PATH)  # noqa: E402


class ChatSession:
    """In-memory chat session tracking chat history and optional memory note."""

    def __init__(self) -> None:
        self.chat_history_lines: List[str] = []
        self.memory_text: Optional[str] = None

    def get_chat_history(self) -> str:
        return "\n".join(self.chat_history_lines)

    def append_turn(self, user_text: str, assistant_text: str) -> None:
        self.chat_history_lines.append(f"user: {user_text}")
        self.chat_history_lines.append(f"assistant: {assistant_text}")


def _print_banner() -> None:
    print(f"Active agent path: {ACTIVE_AGENT_PATH}")
    models = pa._active_models()
    print(f"Active models: router={models.get('router')} | domain={models.get('domain')} | synth={models.get('synth')}")
    print("")
    print("Type '/help' for commands. Press Ctrl+C or type '/exit' to quit.")
    print("")


def _print_help() -> None:
    print("Available commands:")
    print("  /help            Show this help")
    print("  /models          Show active models")
    print("  /memory          Show current memory text")
    print("  /setmem <text>   Set memory text for the session")
    print("  /clearmem        Clear memory text")
    print("  /history         Show chat history")
    print("  /clear           Clear chat history")
    print("  /exit            Exit the chat")


def _print_agent_result(ret: pa.AgentResult) -> None:
    # Mirror hierarchical.main output formatting
    results = ret.results or []
    report_lines: List[str] = []
    for dr in results:
        traces = dr.traces or []
        report_lines.append(f"Domain: {dr.name}")
        if getattr(dr, "intent", None):
            report_lines.append(f"Intent: {dr.intent}")
        if getattr(dr, "duration_secs", None) is not None:
            try:
                report_lines.append(f"Duration: {float(dr.duration_secs):.2f}s")
            except Exception:
                pass
        for t in traces:
            report_lines.append(f"- {t.tool}")
            try:
                args_str = json.dumps(getattr(t, "args", None), ensure_ascii=False)
            except Exception:
                args_str = "null"
            report_lines.append(f"  args: {args_str}")
            report_lines.append(f"  output: {t.output}")
        report_lines.append("")
    if report_lines:
        print("\n".join(report_lines).strip())
        print("\n---\n")
    print(ret.final)
    if ret.timings:
        print("\nTimings:")
        for tm in ret.timings:
            try:
                print(f"- {tm.name}: {tm.seconds:.2f}s")
            except Exception:
                print(f"- {tm.name}: {tm.seconds}")


_GLOBAL_LOOP: Optional[asyncio.AbstractEventLoop] = None


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _GLOBAL_LOOP
    if _GLOBAL_LOOP and not _GLOBAL_LOOP.is_closed():
        return _GLOBAL_LOOP
    try:
        _GLOBAL_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_GLOBAL_LOOP)
    except Exception:
        _GLOBAL_LOOP = asyncio.get_event_loop()
    return _GLOBAL_LOOP


def _invoke_agent(prompt: str, chat_history: Optional[str], memory: Optional[str]) -> pa.AgentResult:
    loop = _ensure_loop()
    return loop.run_until_complete(pa.run_agent(prompt, chat_history=chat_history, memory=memory))


def chat_loop(initial_memory: Optional[str] = None) -> None:
    session = ChatSession()
    session.memory_text = initial_memory
    _print_banner()
    while True:
        try:
            user_in = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            break
        if not user_in:
            continue

        if user_in.startswith("/"):
            cmd, *rest = user_in.split(" ", 1)
            arg = rest[0] if rest else ""
            if cmd in {"/exit", "/quit"}:
                break
            if cmd == "/help":
                _print_help()
                continue
            if cmd == "/models":
                _print_banner()
                continue
            if cmd == "/memory":
                print(session.memory_text or "<no memory set>")
                continue
            if cmd == "/setmem":
                session.memory_text = arg or None
                print("[memory updated]")
                continue
            if cmd == "/clearmem":
                session.memory_text = None
                print("[memory cleared]")
                continue
            if cmd == "/history":
                print(session.get_chat_history() or "<empty>")
                continue
            if cmd == "/clear":
                session.chat_history_lines = []
                print("[history cleared]")
                continue
            print("Unknown command. Type '/help' for available commands.")
            continue

        # Invoke agent with previous chat history (not including this prompt)
        prior_history = session.get_chat_history()
        t0 = time.perf_counter()
        ret = _invoke_agent(user_in, chat_history=prior_history, memory=session.memory_text)
        elapsed = time.perf_counter() - t0
        if isinstance(ret, pa.AgentResult):
            _print_agent_result(ret)
            print(f"\nWrapper elapsed: {elapsed:.2f}s")
            # Append to chat history after printing
            session.append_turn(user_in, ret.final)
        else:
            print(str(ret))
            print(f"\nWrapper elapsed: {elapsed:.2f}s")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive CLI chat for the Hierarchical Agent")
    parser.add_argument("--memory", type=str, default=None, help="Initial memory text to provide to the agent each turn")
    args = parser.parse_args(argv)
    # Preload extensions and schema to reduce per-turn latency
    try:
        pa.initialize_runtime()
    except Exception:
        pass
    chat_loop(initial_memory=args.memory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


