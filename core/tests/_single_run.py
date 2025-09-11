import argparse
import importlib.util
import json
import os
import sys


def _import_module_from_path(path: str):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _flatten_called_tools(res_obj):
    try:
        # Prefer top-level minimal traces if present; otherwise fall back to per-domain traces
        top = getattr(res_obj, "traces", None)
        ordered: list = []
        seen = set()

        def _add(name: object):
            if isinstance(name, str) and name and name not in seen:
                seen.add(name)
                ordered.append(name)

        if isinstance(top, list) and top:
            for t in top:
                name = getattr(t, "tool", None) if hasattr(t, "tool") else (t.get("tool") if isinstance(t, dict) else None)
                _add(name)
            return ordered

        # Fallback: collect from per-domain traces
        results = getattr(res_obj, "results", []) or []
        for dr in results:
            tlist = getattr(dr, "traces", []) or []
            for t in tlist:
                name = getattr(t, "tool", None) if hasattr(t, "tool") else (t.get("tool") if isinstance(t, dict) else None)
                _add(name)
        return ordered
    except Exception:
        return []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True)
    parser.add_argument("--tool-root", required=False, default=None)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args(argv)

    # Ensure project root on sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        mod = _import_module_from_path(args.agent)
        # invoke agent in a fresh loop to avoid interference
        import asyncio

        async def _run():
            return await mod.run_agent(args.prompt, tool_root=args.tool_root)

        try:
            result = asyncio.run(_run())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(_run())
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        # Normalize output
        final = getattr(result, "final", None)
        final_text = final if isinstance(final, str) else str(result)
        called = _flatten_called_tools(result)
        print(json.dumps({"final": final_text, "called_tools": called}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"final": f"<adapter error: {e}>", "called_tools": []}, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


