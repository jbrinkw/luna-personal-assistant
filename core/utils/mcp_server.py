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
    from fastmcp.server.auth.providers.github import GitHubProvider, GitHubTokenVerifier
    from fastmcp.server.auth import AccessToken
    from starlette.applications import Starlette
    from starlette.routing import Mount
    import uvicorn
    import httpx
except Exception as e:
    raise SystemExit(
        "fastmcp and starlette are required. Install with: pip install fastmcp starlette uvicorn"
    ) from e

from core.utils.tool_discovery import get_mcp_enabled_tools


class RestrictedGitHubTokenVerifier(GitHubTokenVerifier):
    """GitHub token verifier with optional username restriction."""
    
    def __init__(self, allowed_username: str = None, **kwargs):
        super().__init__(**kwargs)
        self.allowed_username = allowed_username
    
    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify token and check if user is allowed."""
        # First do standard GitHub token verification
        access_token = await super().verify_token(token)
        
        if access_token is None:
            return None
        
        # If username restriction is enabled, check it
        if self.allowed_username:
            # Get the GitHub username from claims (set by GitHubTokenVerifier)
            username = access_token.claims.get("login")
            
            if not username:
                print("[MCP Auth] Access denied: No GitHub username found in token")
                return None
            
            if username != self.allowed_username:
                print(f"[MCP Auth] Access denied for user '{username}'. Only '{self.allowed_username}' is allowed.")
                return None
            
            print(f"[MCP Auth] Access granted for user '{username}'")
        
        return access_token


class RestrictedGitHubProvider(GitHubProvider):
    """GitHub OAuth provider with optional username restriction.
    
    This overrides GitHubProvider to inject a custom token verifier
    that checks GitHub usernames against ALLOWED_GITHUB_USERNAME.
    """
    
    def __init__(
        self,
        allowed_username: str = None,
        client_id: str = None,
        client_secret: str = None,
        base_url: str = None,
        **kwargs
    ):
        """Initialize with username restriction.
        
        We have to override the entire __init__ because GitHubProvider
        creates the token_verifier before calling super().__init__().
        """
        from fastmcp.server.auth.providers.github import GitHubProviderSettings
        from fastmcp.utilities.types import NotSet
        from pydantic import SecretStr
        
        # Process settings like GitHubProvider does
        settings = GitHubProviderSettings.model_validate(
            {
                k: v
                for k, v in {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "base_url": base_url,
                    **kwargs
                }.items()
                if v is not None
            }
        )
        
        # Apply defaults
        timeout_seconds_final = settings.timeout_seconds or 10
        required_scopes_final = settings.required_scopes or ["user"]
        allowed_client_redirect_uris_final = settings.allowed_client_redirect_uris
        
        # Create OUR restricted token verifier instead of the standard one
        if allowed_username:
            token_verifier = RestrictedGitHubTokenVerifier(
                allowed_username=allowed_username,
                required_scopes=required_scopes_final,
                timeout_seconds=timeout_seconds_final,
            )
        else:
            from fastmcp.server.auth.providers.github import GitHubTokenVerifier
            token_verifier = GitHubTokenVerifier(
                required_scopes=required_scopes_final,
                timeout_seconds=timeout_seconds_final,
            )
        
        # Extract secret string from SecretStr
        client_secret_str = (
            settings.client_secret.get_secret_value() if settings.client_secret else ""
        )
        
        # Initialize OAuthProxy parent (skip GitHubProvider.__init__)
        from fastmcp.server.auth.oauth_proxy import OAuthProxy
        OAuthProxy.__init__(
            self,
            upstream_authorization_endpoint="https://github.com/login/oauth/authorize",
            upstream_token_endpoint="https://github.com/login/oauth/access_token",
            upstream_client_id=settings.client_id,
            upstream_client_secret=client_secret_str,
            token_verifier=token_verifier,
            base_url=settings.base_url,
            redirect_path=settings.redirect_path,
            issuer_url=settings.base_url,
            allowed_client_redirect_uris=allowed_client_redirect_uris_final,
            client_storage=kwargs.get('client_storage'),
        )


def _register_tools(mcp: "FastMCP", tools: List[Callable[..., Any]]) -> int:
    """Register tools with the MCP server."""
    from core.utils.tool_discovery import MCPRemoteTool
    import inspect
    
    count = 0
    for fn in tools:
        try:
            # Handle remote MCP tools differently
            if isinstance(fn, MCPRemoteTool):
                # Create a proper function with explicit parameters from schema
                tool_name = fn.__name__
                tool_doc = fn.__doc__
                input_schema = fn.input_schema
                
                # Build function with explicit parameters
                if input_schema and isinstance(input_schema, dict):
                    properties = input_schema.get('properties', {})
                    required = input_schema.get('required', [])
                    
                    # Create parameter list
                    params = []
                    param_names = []
                    annotations = {}
                    
                    for param_name, param_info in properties.items():
                        param_names.append(param_name)
                        param_type = param_info.get('type', 'string')
                        
                        # Map JSON schema types to Python types
                        if param_type == 'string':
                            py_type = str
                        elif param_type in ('number', 'integer'):
                            py_type = float if param_type == 'number' else int
                        elif param_type == 'boolean':
                            py_type = bool
                        else:
                            py_type = str
                        
                        annotations[param_name] = py_type
                        
                        # Add parameter with default if not required
                        if param_name in required:
                            params.append(inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=py_type))
                        else:
                            params.append(inspect.Parameter(param_name, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None, annotation=py_type))
                    
                    # Create function with proper signature
                    def create_remote_tool_func(remote_tool_instance, param_list):
                        def tool_func(*args, **kwargs):
                            # Convert args/kwargs to dict for remote call
                            call_kwargs = dict(zip(param_list, args))
                            call_kwargs.update(kwargs)
                            # Remove None values
                            call_kwargs = {k: v for k, v in call_kwargs.items() if v is not None}
                            return remote_tool_instance(**call_kwargs)
                        
                        tool_func.__name__ = remote_tool_instance.__name__
                        tool_func.__doc__ = remote_tool_instance.__doc__
                        tool_func.__signature__ = inspect.Signature(params)
                        tool_func.__annotations__ = annotations
                        return tool_func
                    
                    wrapper_fn = create_remote_tool_func(fn, param_names)
                else:
                    # No schema, create simple wrapper
                    def tool_func():
                        return fn()
                    tool_func.__name__ = tool_name
                    tool_func.__doc__ = tool_doc
                    wrapper_fn = tool_func
                
                mcp.tool(wrapper_fn)
                count += 1
            else:
                # Regular local tool
                mcp.tool(fn)
                count += 1
        except Exception as e:
            # Skip tools that fail to register
            print(f"[WARNING] Failed to register tool {getattr(fn, '__name__', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()
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
    
    # Get MCP-specific GitHub credentials
    # MCP uses separate OAuth app from Hub UI for cleaner separation
    client_id = os.getenv("MCP_GITHUB_CLIENT_ID")
    client_secret = os.getenv("MCP_GITHUB_CLIENT_SECRET")
    allowed_username = os.getenv("ALLOWED_GITHUB_USERNAME")
    
    if not client_id or not client_secret:
        print("[ERROR] MCP_GITHUB_CLIENT_ID and MCP_GITHUB_CLIENT_SECRET not set in environment")
        print("\nTo set up MCP GitHub OAuth:")
        print("  1. Register a NEW OAuth app at: https://github.com/settings/developers")
        print(f"  2. Set redirect URI to: {base_url}/auth/callback")
        print("  3. Add credentials to .env:")
        print("     MCP_GITHUB_CLIENT_ID=your_mcp_client_id")
        print("     MCP_GITHUB_CLIENT_SECRET=your_mcp_client_secret")
        print("\nNote: This is separate from GITHUB_CLIENT_ID used by Hub UI")
        return 1
    
    # Log username restriction status
    if allowed_username:
        print(f"[MCP] Access restricted to GitHub user: {allowed_username}")
    else:
        print("[MCP] WARNING: ALLOWED_GITHUB_USERNAME not set - any GitHub user can connect")
        print("[MCP] Set ALLOWED_GITHUB_USERNAME in .env to restrict access")
    
    # Create MCP server with GitHub OAuth
    print("[MCP] Setting up OAuth 2.1 authentication for Anthropic Claude")
    print("[MCP] Provider: GitHub")
    print(f"[MCP] Base URL: {base_url}")
    
    try:
        # Create GitHub auth provider with username restriction
        # base_url: OAuth operational endpoints (/authorize, /token, /callback)
        auth_provider = RestrictedGitHubProvider(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            allowed_username=allowed_username
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

    # Initialize remote MCP session manager if configured
    session_manager = None
    try:
        import json
        from pathlib import Path
        master_config_path = Path(PROJECT_ROOT) / 'core' / 'master_config.json'
        if master_config_path.exists():
            with open(master_config_path, 'r') as f:
                master_config = json.load(f)
            
            # Check if remote MCP servers are configured
            remote_servers = master_config.get('remote_mcp_servers', {})
            if remote_servers:
                print(f"[MCP] Initializing {len(remote_servers)} remote MCP server(s)...")
                import asyncio
                from core.utils.remote_mcp_session_manager import RemoteMCPSessionManager
                
                session_manager = RemoteMCPSessionManager(master_config)
                asyncio.run(session_manager.initialize_all())
    except Exception as e:
        print(f"[MCP] Warning: Failed to initialize remote MCP servers: {e}")
        import traceback
        traceback.print_exc()
    
    # Load and register MCP-enabled tools (local + remote)
    print("[MCP] Discovering tools from all sources...", flush=True)
    try:
        tools = get_mcp_enabled_tools(session_manager=session_manager)
        print(f"[MCP] Found {len(tools)} total tools (local + remote)", flush=True)
        registered = _register_tools(mcp, tools)
        print(f"[MCP] Successfully registered {registered} tools", flush=True)
        
        if registered == 0:
            print("[WARNING] No tools registered. Check extension tool_config.json files.", flush=True)
    except Exception as e:
        print(f"[MCP] ERROR during tool discovery/registration: {e}", flush=True)
        import traceback
        traceback.print_exc()
        registered = 0

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

