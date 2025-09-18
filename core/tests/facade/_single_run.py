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


def _collect_tool_traces(res_obj):
    try:
        traces_out = []
        # Prefer top-level traces if present
        top = getattr(res_obj, "traces", None)
        if isinstance(top, list) and top:
            for t in top:
                try:
                    tool = getattr(t, "tool", None) if hasattr(t, "tool") else (t.get("tool") if isinstance(t, dict) else None)
                    args = getattr(t, "args", None) if hasattr(t, "args") else (t.get("args") if isinstance(t, dict) else None)
                    output = getattr(t, "output", None) if hasattr(t, "output") else (t.get("output") if isinstance(t, dict) else None)
                    duration = getattr(t, "duration_secs", None) if hasattr(t, "duration_secs") else (t.get("duration_secs") if isinstance(t, dict) else None)
                    traces_out.append({"tool": tool, "args": args, "output": output, "duration_secs": duration})
                except Exception:
                    continue
            return traces_out

        # Fallback: aggregate from per-domain results
        results = getattr(res_obj, "results", []) or []
        for dr in results:
            try:
                domain = getattr(dr, "name", None) if hasattr(dr, "name") else (dr.get("name") if isinstance(dr, dict) else None)
            except Exception:
                domain = None
            tlist = getattr(dr, "traces", []) or []
            for t in tlist:
                try:
                    tool = getattr(t, "tool", None) if hasattr(t, "tool") else (t.get("tool") if isinstance(t, dict) else None)
                    args = getattr(t, "args", None) if hasattr(t, "args") else (t.get("args") if isinstance(t, dict) else None)
                    output = getattr(t, "output", None) if hasattr(t, "output") else (t.get("output") if isinstance(t, dict) else None)
                    duration = getattr(t, "duration_secs", None) if hasattr(t, "duration_secs") else (t.get("duration_secs") if isinstance(t, dict) else None)
                    item = {"tool": tool, "args": args, "output": output, "duration_secs": duration}
                    if domain:
                        item["domain"] = domain
                    traces_out.append(item)
                except Exception:
                    continue
        return traces_out
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
        traces = _collect_tool_traces(result)
        # Extract human-readable error lines from traces (best-effort)
        errors: list = []
        for tr in traces:
            out = tr.get("output") if isinstance(tr, dict) else None
            try:
                s = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
            except Exception:
                s = str(out)
            if isinstance(s, str) and s and ("Error" in s or "error" in s):
                errors.append({"tool": tr.get("tool"), "message": s})
        print(json.dumps({"final": final_text, "called_tools": called, "tool_traces": traces, "errors": errors}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"final": f"<adapter error: {e}>", "called_tools": []}, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


