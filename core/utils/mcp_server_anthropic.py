"""MCP Server for Luna - Configured for Anthropic Claude Remote Connection

Uses FastMCP's RemoteAuthProvider with OAuth 2.1 for user authentication.
Supports Anthropic's Claude web/desktop app connecting remotely.
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
    from fastmcp.server.auth.providers.github import GitHubProvider
    from fastmcp.server.auth.providers.google import GoogleProvider
    from fastmcp.server.auth.providers.azure import AzureProvider
except Exception as e:
    raise SystemExit(
        "fastmcp is required. Install with: pip install fastmcp"
    ) from e

try:
    from starlette.middleware.cors import CORSMiddleware
except ImportError:
    CORSMiddleware = None

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
    """Main entry point for Anthropic-compatible MCP server."""
    parser = argparse.ArgumentParser(description="Luna MCP server for Anthropic Claude")
    parser.add_argument("--name", default="Luna MCP", help="MCP server name")
    parser.add_argument("--transport", choices=["sse", "stdio", "http", "streamable-http"], default="streamable-http", help="Transport protocol")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE (0.0.0.0 for network access)")
    parser.add_argument("--port", type=int, default=8765, help="Port for SSE")
    parser.add_argument("--provider", default="github", choices=["github", "google", "azure"],
                       help="OAuth provider (github, google, or azure)")
    args = parser.parse_args(argv)

    # Get base URL (required for OAuth redirects)
    base_url = os.getenv("MCP_BASE_URL")
    
    # Auto-generate from NGROK_DOMAIN (preferred) or LT_SUBDOMAIN (legacy)
    if not base_url:
        ngrok_domain = os.getenv("NGROK_DOMAIN")
        if ngrok_domain:
            base_url = f"https://{ngrok_domain}"
            print(f"[MCP] Auto-generated base URL from NGROK_DOMAIN: {base_url}")
        else:
            lt_subdomain = os.getenv("LT_SUBDOMAIN")
            if lt_subdomain:
                base_url = f"https://{lt_subdomain}.loca.lt"
                print(f"[MCP] Auto-generated base URL from LT_SUBDOMAIN: {base_url}")
            else:
                print("[ERROR] Neither MCP_BASE_URL, NGROK_DOMAIN, nor LT_SUBDOMAIN set in .env")
                print("[ERROR] Set one of:")
                print("[ERROR]   NGROK_DOMAIN=your-domain.ngrok-free.app (recommended)")
                print("[ERROR]   LT_SUBDOMAIN=your-unique-name (legacy)")
                print("[ERROR]   MCP_BASE_URL=https://your-domain.com")
                return 1
    
    # Get provider-specific credentials and create auth provider
    if args.provider == "github":
        client_id = os.getenv("GITHUB_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        provider_class = GitHubProvider
        setup_url = "https://github.com/settings/developers"
    elif args.provider == "google":
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        provider_class = GoogleProvider
        setup_url = "https://console.cloud.google.com/apis/credentials"
    elif args.provider == "azure":
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")
        provider_class = AzureProvider
        setup_url = "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"
    else:
        print(f"[ERROR] Unknown provider: {args.provider}")
        return 1
    
    if not client_id or not client_secret:
        print(f"[ERROR] {args.provider.upper()}_CLIENT_ID and {args.provider.upper()}_CLIENT_SECRET not set in .env")
        print(f"\nTo set up {args.provider.upper()} OAuth:")
        print(f"  1. Register an OAuth app at: {setup_url}")
        print(f"  2. Set redirect URI to: {base_url}/auth/callback")
        print(f"  3. Add credentials to .env:")
        print(f"     {args.provider.upper()}_CLIENT_ID=your_client_id")
        print(f"     {args.provider.upper()}_CLIENT_SECRET=your_client_secret")
        return 1
    
    # Create MCP server with OAuth provider
    print("[MCP] Setting up OAuth 2.1 authentication for Anthropic Claude")
    print(f"[MCP] Provider: {args.provider}")
    print(f"[MCP] Base URL: {base_url}")
    
    try:
        # Create provider-specific auth
        auth_provider = provider_class(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )
        
        # Create FastMCP with auth - don't specify paths, let FastMCP use defaults
        mcp = FastMCP(
            name=args.name,
            auth=auth_provider
        )
        
        print(f"[MCP] ✓ OAuth 2.1 authentication enabled")
        print(f"[MCP] Users will authenticate via {args.provider.upper()}")
        
    except Exception as e:
        print(f"[ERROR] Failed to set up OAuth: {e}")
        import traceback
        traceback.print_exc()
        print("[ERROR] MCP server cannot start without authentication")
        return 1

    # Load and register MCP-enabled tools
    tools = get_mcp_tools()
    registered = _register_tools(mcp, tools)

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
        print(f"  OAuth Provider: {args.provider.upper()}")
        print(f"{'='*60}\n")
        
        # Run with specified transport
        # For OAuth remote MCP, set the MCP endpoint path to root
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

