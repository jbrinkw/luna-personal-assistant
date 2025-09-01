"""Local ChefByte tools (no MCP decorators).

Re-exports CHEF_* functions from push, pull, and action tool modules for direct import.
"""

from __future__ import annotations

try:
    import push_tools as _push
    import pull_tools as _pull
    import action_tools as _action
except ModuleNotFoundError:
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.abspath(_os.path.dirname(__file__)))
    import push_tools as _push  # type: ignore
    import pull_tools as _pull  # type: ignore
    import action_tools as _action  # type: ignore


__all__: list[str] = []

def _unwrap_callable(obj):
    """Return a real Python callable for a FastMCP FunctionTool or pass-through.

    FastMCP decorators wrap functions as FunctionTool instances which are not
    directly callable by LangChain's create_react_agent. Those expose the
    original function via the `.fn` attribute. This helper returns `.fn` when
    present; otherwise returns the object if it is already callable; else None.
    """
    try:
        # FastMCP FunctionTool exposes the original function as `.fn`
        fn = getattr(obj, "fn", None)
        if callable(fn):
            return fn
    except Exception:
        pass
    return obj if callable(obj) else None


def _export_from(mod) -> None:
    for name in dir(mod):
        if not name.startswith("CHEF_"):
            continue
        wrapped = _unwrap_callable(getattr(mod, name))
        if wrapped is None:
            continue
        globals()[name] = wrapped
        __all__.append(name)


_export_from(_push)
_export_from(_pull)
_export_from(_action)



