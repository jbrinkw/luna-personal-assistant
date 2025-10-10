"""MCP Server for Luna - Fast MCP + SSE with Bearer token auth.

Exposes tools from extensions with enabled_in_mcp=true via SSE endpoint.
Single-file server module implementing the spec.
"""
import os
import sys
import argparse
from typing import Any, Callable, List
from pathlib import Path

# Ensure project root importability
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from fastmcp import FastMCP
except Exception as e:
    raise SystemExit("fastmcp is required. Install with: pip install fastmcp") from e

from core.utils.extension_discovery import get_mcp_tools


def _register_tools(mcp: "FastMCP", tools: List[Callable[..., Any]]) -> int:
    """Register tools with the MCP server."""
    count = 0
    for fn in tools:
        try:
            mcp.tool(fn)
            count += 1
        except Exception:
            # Skip tools that fail to register
            continue
    return count


def main(argv: List[str]) -> int:
    """Main entry point for MCP server."""
    parser = argparse.ArgumentParser(description="Luna MCP server")
    parser.add_argument("--name", default="Luna MCP", help="MCP server name")
    parser.add_argument("--transport", choices=["sse", "stdio"], default="sse", help="Transport protocol")
    parser.add_argument("--host", default="127.0.0.1", help="Host for SSE")
    parser.add_argument("--port", type=int, default=8765, help="Port for SSE")
    parser.add_argument("--auth-token", default=None, help="Bearer token for authentication (defaults to MCP_AUTH_TOKEN env var)")
    args = parser.parse_args(argv)

    # Get auth token from args or environment
    auth_token = args.auth_token or os.getenv("MCP_AUTH_TOKEN")
    
    # Create MCP server with optional Bearer token auth
    if auth_token:
        # Use static token verification via FastMCP's built-in auth
        try:
            from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
            
            # Create token verifier
            token_map = {
                auth_token: {
                    "client_id": "luna-client",
                    "scopes": [],
                }
            }
            auth_provider = StaticTokenVerifier(tokens=token_map, required_scopes=None)
            mcp = FastMCP(args.name, auth=auth_provider)
        except Exception:
            # Fallback to no auth if StaticTokenVerifier not available
            print("[WARNING] Could not set up auth, running without authentication")
            mcp = FastMCP(args.name)
    else:
        mcp = FastMCP(args.name)

    # Load and register MCP-enabled tools
    tools = get_mcp_tools()
    registered = _register_tools(mcp, tools)

    if args.transport == "sse":
        url = f"http://{args.host}:{args.port}/sse"
        print(f"[MCP] {args.name}: {registered} tools registered. Serving via SSE at {url}")
        if auth_token:
            print(f"[MCP] Bearer token authentication enabled")
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        print(f"[MCP] {args.name}: {registered} tools registered. Serving via STDIO")
        mcp.run(transport="stdio")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

