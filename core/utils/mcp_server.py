"""MCP Server for Luna - Production Version with Tool Auto-Discovery

Uses FastMCP's RemoteAuthProvider with OAuth 2.1 for user authentication.
Supports Anthropic's Claude web/desktop app connecting remotely.
Auto-discovers and registers all MCP-enabled tools from Luna extensions.
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
    load_dotenv(override=True)  # Override environment variables from parent process
except Exception:
    pass

try:
    from fastmcp import FastMCP
    from fastmcp.server.auth.providers.github import GitHubProvider
    from starlette.applications import Starlette
    from starlette.routing import Mount
    import uvicorn
except Exception as e:
    raise SystemExit(
        "fastmcp and starlette are required. Install with: pip install fastmcp starlette uvicorn"
    ) from e

from core.utils.extension_discovery import get_mcp_tools


def _register_tools(mcp: "FastMCP", tools: List[Callable[..., Any]]) -> int:
    """Register tools with the MCP server."""
    count = 0
    for fn in tools:
        try:
            mcp.tool(fn)
            count += 1
        except Exception as e:
            # Skip tools that fail to register
            print(f"[WARNING] Failed to register tool {fn.__name__}: {e}")
            continue
    return count


def main(argv: List[str]) -> int:
    """Main entry point for Anthropic-compatible MCP server."""
    parser = argparse.ArgumentParser(description="Luna MCP server for Anthropic Claude")
    parser.add_argument("--name", default="Luna MCP", help="MCP server name")
    parser.add_argument("--transport", choices=["sse", "stdio", "http", "streamable-http"], default="streamable-http", help="Transport protocol")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE (0.0.0.0 for network access)")
    parser.add_argument("--port", type=int, default=8765, help="Port for SSE")
    args = parser.parse_args(argv)

    # Get URLs for OAuth configuration
    # base_url: Where OAuth endpoints live (e.g., https://lunahub.dev/api)
    # issuer_url: Where .well-known discovery lives (e.g., https://lunahub.dev)
    base_url = os.getenv("PUBLIC_URL", "https://lunahub.dev/api")
    issuer_url = os.getenv("ISSUER_URL", "https://lunahub.dev")
    
    print(f"[MCP] Base URL (OAuth endpoints): {base_url}")
    print(f"[MCP] Issuer URL (discovery): {issuer_url}")
    
    # Get GitHub credentials
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("[ERROR] GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET not set in environment")
        print("\nTo set up GitHub OAuth:")
        print("  1. Register an OAuth app at: https://github.com/settings/developers")
        print(f"  2. Set redirect URI to: {base_url}/auth/callback")
        print("  3. Add credentials to .env:")
        print("     GITHUB_CLIENT_ID=your_client_id")
        print("     GITHUB_CLIENT_SECRET=your_client_secret")
        return 1
    
    # Create MCP server with GitHub OAuth
    print("[MCP] Setting up OAuth 2.1 authentication for Anthropic Claude")
    print("[MCP] Provider: GitHub")
    print(f"[MCP] Base URL: {base_url}")
    
    try:
        # Create GitHub auth provider
        # base_url: OAuth operational endpoints (/authorize, /token, /callback)
        auth_provider = GitHubProvider(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )
        
        # Create FastMCP with auth
        mcp = FastMCP(
            name=args.name,
            auth=auth_provider
        )
        
        print("[MCP] ✓ OAuth 2.1 authentication enabled")
        print("[MCP] Users will authenticate via GITHUB")
        
    except Exception as e:
        print(f"[ERROR] Failed to set up OAuth: {e}")
        import traceback
        traceback.print_exc()
        print("[ERROR] MCP server cannot start without authentication")
        return 1

    # Load and register MCP-enabled tools
    print("[MCP] Discovering tools from Luna extensions...")
    tools = get_mcp_tools()
    registered = _register_tools(mcp, tools)
    
    if registered == 0:
        print("[WARNING] No tools registered. Check extension tool_config.json files.")

    if args.transport in ["sse", "http", "streamable-http"]:
        url = f"http://{args.host}:{args.port}"
        transport_name = "Streamable HTTP" if args.transport == "streamable-http" else args.transport.upper()
        
        # Use ASGI mounting approach for proper subpath support
        print("[MCP] Using ASGI mounting for subpath support...")
        
        try:
            # Create MCP ASGI app mounted at /mcp
            mcp_app = mcp.http_app(path="/mcp")
            
            # Well-known routes will be handled by the MCP app itself
            # FastMCP automatically creates OAuth discovery endpoints
            well_known_routes = []
            print("[MCP] ⚠ OAuth discovery handled by MCP app (no separate well-known routes)")
            
            # Create Starlette app with proper mounting
            # /api/* → MCP app (includes /api/mcp, /api/authorize, /api/token, etc.)
            # /.well-known/* → OAuth discovery routes at root
            app = Starlette(
                routes=[
                    Mount("/api", mcp_app),
                    *well_known_routes
                ],
                lifespan=getattr(mcp_app, 'lifespan', None)
            )
            
            print(f"\n{'='*60}")
            print(f"[MCP] {args.name}")
            print(f"[MCP] {registered} tools registered")
            print(f"[MCP] Serving via {transport_name} at {url}")
            print(f"[MCP] MCP Endpoint: {base_url}/mcp")
            print(f"[MCP] OAuth Authorize: {base_url}/authorize")
            print(f"[MCP] OAuth Discovery: {issuer_url}/.well-known/oauth-authorization-server")
            print(f"\n[ANTHROPIC] Add to Claude:")
            print(f"  MCP Server URL: {base_url}/mcp")
            print(f"  OAuth Provider: GITHUB")
            print(f"{'='*60}\n")
            
            # Run with Uvicorn instead of mcp.run()
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
            
        except Exception as e:
            print(f"[ERROR] Failed to create ASGI app: {e}")
            import traceback
            traceback.print_exc()
            print("[INFO] Falling back to standard mcp.run()...")
            
            # Fallback to original approach
            print(f"\n{'='*60}")
            print(f"[MCP] {args.name}")
            print(f"[MCP] {registered} tools registered")
            print(f"[MCP] Serving via {transport_name} at {url}")
            print(f"[MCP] Public URL: {base_url}")
            print(f"\n[ANTHROPIC] Add to Claude:")
            print(f"  MCP Server URL: {base_url}")
            print(f"  OAuth Provider: GITHUB")
            print(f"{'='*60}\n")
            
            if args.transport == "streamable-http":
                mcp.run(transport=args.transport, host=args.host, port=args.port, path="/")
            else:
                mcp.run(transport=args.transport, host=args.host, port=args.port)
    else:
        print(f"[MCP] {args.name}: {registered} tools registered")
        print(f"[MCP] Serving via STDIO")
        print(f"[WARNING] OAuth not applicable for STDIO transport")
        mcp.run(transport="stdio")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

