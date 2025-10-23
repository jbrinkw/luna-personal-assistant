"""MCP Server for Luna - Configured for Anthropic Claude Remote Connection

Uses FastMCP's RemoteAuthProvider with OAuth 2.1 for user authentication.
Supports Anthropic's Claude web/desktop app connecting remotely.
"""
import os
import sys
import argparse
from typing import List
from pathlib import Path

# Optional .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from fastmcp import FastMCP
    from fastmcp.server.auth.providers.github import GitHubProvider
except Exception as e:
    raise SystemExit(
        "fastmcp is required. Install with: pip install fastmcp"
    ) from e


def main(argv: List[str]) -> int:
    """Main entry point for Anthropic-compatible MCP server."""
    parser = argparse.ArgumentParser(description="Luna MCP server for Anthropic Claude")
    parser.add_argument("--name", default="Luna MCP", help="MCP server name")
    parser.add_argument("--transport", choices=["sse", "stdio", "http", "streamable-http"], default="streamable-http", help="Transport protocol")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE (0.0.0.0 for network access)")
    parser.add_argument("--port", type=int, default=8765, help="Port for SSE")
    args = parser.parse_args(argv)

    # Get base URL (required for OAuth redirects)
    base_url = os.getenv("PUBLIC_URL")
    
    if not base_url:
        print("[ERROR] PUBLIC_URL not set in environment")
        print("[ERROR] Set PUBLIC_URL=https://your-domain.com")
        return 1
    
    # Get GitHub credentials
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("[ERROR] GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET not set in environment")
        print("\nTo set up GitHub OAuth:")
        print("  1. Register an OAuth app at: https://github.com/settings/developers")
        print(f"  2. Set redirect URI to: {base_url}/auth/callback")
        print("  3. Add credentials to environment:")
        print("     GITHUB_CLIENT_ID=your_client_id")
        print("     GITHUB_CLIENT_SECRET=your_client_secret")
        return 1
    
    # Create MCP server with GitHub OAuth
    print("[MCP] Setting up OAuth 2.1 authentication for Anthropic Claude")
    print("[MCP] Provider: GitHub")
    print(f"[MCP] Base URL: {base_url}")
    
    try:
        # Create GitHub auth provider
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

    # Register simple tools
    @mcp.tool()
    def get_weather() -> str:
        """Get the current weather"""
        return "cold"
    
    @mcp.tool()
    def get_verginity() -> bool:
        """Get verginity status"""
        return True
    
    registered = 2

    if args.transport in ["sse", "http", "streamable-http"]:
        url = f"http://{args.host}:{args.port}"
        transport_name = "Streamable HTTP" if args.transport == "streamable-http" else args.transport.upper()
        print(f"\n{'='*60}")
        print(f"[MCP] {args.name}")
        print(f"[MCP] {registered} tools registered")
        print(f"[MCP] Serving via {transport_name} at {url}")
        print(f"[MCP] Public URL: {base_url}")
        print(f"\n[ANTHROPIC] Add to Claude:")
        print(f"  MCP Server URL: {base_url}")
        print(f"  OAuth Provider: GITHUB")
        print(f"{'='*60}\n")
        
        # Run with specified transport
        if args.transport == "streamable-http":
            mcp.run(transport=args.transport, host=args.host, port=args.port, path="/")
    else:
        print(f"[MCP] {args.name}: {registered} tools registered")
        print(f"[MCP] Serving via STDIO")
        print(f"[WARNING] OAuth not applicable for STDIO transport")
        mcp.run(transport="stdio")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

