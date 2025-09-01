import argparse
import asyncio
import json
import os
import sys
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore

# Allow running both as a module and as a script
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.agent.orchestrator_local import orchestrate


def main() -> None:
    parser = argparse.ArgumentParser(description="Direct Local Agents Chat (GeneralByte + HomeAssistant)")
    parser.add_argument("--once", type=str, default=None, help="Run a single prompt and exit")
    args = parser.parse_args()

    if load_dotenv is not None:
        load_dotenv()

    if args.once is not None:
        out = asyncio.run(orchestrate(args.once))
        print(json.dumps(out, indent=2))
        return

    print("Direct chat ready. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input.strip():
            continue
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        try:
            out = asyncio.run(orchestrate(user_input))
        except Exception as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            continue
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()


