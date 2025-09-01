"""Run the GeneralByte MCP server with Home Assistant tools.

This registers local tool functions (no decorators) from `tool_local.py`
so behavior matches the direct/local usage.
"""

from fastmcp import FastMCP
try:
    import tool_local as gb_local
except ModuleNotFoundError:
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.abspath(_os.path.dirname(__file__)))
    import tool_local as gb_local
mcp = FastMCP("GeneralByte Aggregated Tools")

def _register_tools() -> None:
    mcp.tool(gb_local.GENERAL_ACTION_send_phone_notification)
    mcp.tool(gb_local.GENERAL_GET_todo_list)
    mcp.tool(gb_local.GENERAL_ACTION_modify_todo_item)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the GeneralByte MCP server")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8050, help="Port (default 8050)")
    args = parser.parse_args()

    url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    print(f"[GeneralByte] Running via SSE at {url}")
    _register_tools()
    mcp.run(transport="sse", host=args.host, port=args.port)
