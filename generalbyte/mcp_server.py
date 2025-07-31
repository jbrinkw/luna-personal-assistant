"""Run the GeneralByte MCP server with Home Assistant tools."""

from fastmcp import FastMCP
from . import tool

mcp = FastMCP("GeneralByte Aggregated Tools")

mcp.mount(tool.mcp, prefix="general")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the GeneralByte MCP server")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8050, help="Port (default 8050)")
    args = parser.parse_args()

    url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    print(f"[GeneralByte] Running via SSE at {url}")

    mcp.run(transport="sse", host=args.host, port=args.port)
