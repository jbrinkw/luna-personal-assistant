import asyncio
import json
import os
import sys
import argparse

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

from standalone_orchestrator import orchestrate, ORCHESTRATOR_MODEL, SPECIALIST_MODEL


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone Hierarchical Orchestrator CLI Chat")
    parser.add_argument("--once", type=str, default=None, help="Run a single prompt and exit")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set (load via .env or environment)")
        sys.exit(1)

    if args.once is not None:
        out = asyncio.run(orchestrate(args.once))
        print(json.dumps(out, indent=2))
        return

    print(
        f"Hierarchical chat (orchestrator={ORCHESTRATOR_MODEL}, specialist={SPECIALIST_MODEL}). Type 'exit' to quit."
    )
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


