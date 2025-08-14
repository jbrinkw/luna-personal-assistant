"""Run the ChefByte MCP tool server (aggregate of all tool modules)."""

import asyncio
from fastmcp import FastMCP
try:
    import push_tools
    import pull_tools
    import action_tools
except ModuleNotFoundError:
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__))))
    import push_tools
    import pull_tools
    import action_tools

# Create an aggregator FastMCP server
mcp = FastMCP("ChefByte Aggregated Tools")

mcp.mount(push_tools.mcp, prefix="push")
mcp.mount(pull_tools.mcp, prefix="pull")
mcp.mount(action_tools.mcp, prefix="action")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the aggregated ChefByte MCP server")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default 8000)")
    args = parser.parse_args()

    url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    print(f"[ChefByte Aggregated] Running via SSE at {url}")

    mcp.run(transport="sse", host=args.host, port=args.port)

