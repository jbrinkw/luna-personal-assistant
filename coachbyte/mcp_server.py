"""Run the CoachByte MCP server exposing all workout tools."""

from fastmcp import FastMCP
import tools

mcp = FastMCP("CoachByte Tools")

for name in tools.__all__:
    mcp.tool(getattr(tools, name))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the aggregated CoachByte MCP server",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host (default 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8100,
        help="Port (default 8100)",
    )
    args = parser.parse_args()

    url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    print(f"[CoachByte] Running via SSE at {url}")

    mcp.run(transport="sse", host=args.host, port=args.port)
