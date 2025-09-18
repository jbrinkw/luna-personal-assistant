import os
import sys
import argparse
from typing import Any, Callable, Dict, List

# Ensure project root importability
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Optional .env support
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

try:
    from fastmcp import FastMCP
    from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider
    from fastmcp.server.auth.providers.jwt import JWTVerifier
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
    from fastmcp.server.auth.auth import RemoteAuthProvider
    from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
    from mcp.shared.auth import OAuthClientInformationFull
    from mcp.server.auth.provider import AccessToken as SDKAccessToken
    from mcp.server.auth.provider import AuthorizationCode as SDKAuthorizationCode
    from mcp.server.auth.provider import RefreshToken as SDKRefreshToken
except Exception as e:  # noqa: BLE001
    raise SystemExit("fastmcp is required. Install with: pip install fastmcp") from e

try:
    from core.helpers.light_schema_gen import discover_extensions
except Exception as e:  # noqa: BLE001
    raise SystemExit(f"Failed to import discover_extensions: {e}") from e


def _load_tools(tool_root: str | None = None) -> List[Callable[..., Any]]:
    tools: List[Callable[..., Any]] = []
    try:
        extensions = discover_extensions(tool_root)
    except Exception:
        extensions = []
    for ext in extensions:
        for fn in (ext.get("tools") or []):
            if callable(fn):
                tools.append(fn)
    return tools


def _register_tools(mcp: "FastMCP", tools: List[Callable[..., Any]]) -> int:
    count = 0
    for fn in tools:
        try:
            mcp.tool(fn)
            count += 1
        except Exception:
            # Skip tools that fail to register
            continue
    return count


class FileBackedOAuthProvider(InMemoryOAuthProvider):
    """In-memory OAuth provider with JSON persistence.

    Persists registered clients, auth codes, access/refresh tokens so that
    OAuth clients survive process restarts.
    """

    def __init__(
        self,
        *,
        state_path: str,
        base_url: str,
        resource_server_url: str,
        required_scopes: List[str] | None,
        client_registration_options: ClientRegistrationOptions,
        revocation_options: RevocationOptions,
    ) -> None:
        # Initialize parent
        super().__init__(
            base_url=base_url,
            resource_server_url=resource_server_url,
            required_scopes=required_scopes,
            client_registration_options=client_registration_options,
            revocation_options=revocation_options,
        )
        self._state_path = os.path.abspath(state_path)
        # Ensure directory exists
        try:
            os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
        except Exception:
            pass
        # Load prior state if present
        self._load_state()

    def _save_state(self) -> None:
        try:
            state: Dict[str, Any] = {
                "clients": {cid: c.model_dump() for cid, c in self.clients.items()},
                "auth_codes": {code: ac.model_dump() for code, ac in self.auth_codes.items()},
                "access_tokens": {tok: at.model_dump() for tok, at in self.access_tokens.items()},
                "refresh_tokens": {tok: rt.model_dump() for tok, rt in self.refresh_tokens.items()},
                "access_to_refresh": dict(self._access_to_refresh_map),
                "refresh_to_access": dict(self._refresh_to_access_map),
            }
            tmp = self._state_path + ".tmp"
            import json

            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f)
            os.replace(tmp, self._state_path)
        except Exception:
            # Best-effort persistence; avoid crashing the server
            pass

    def _load_state(self) -> None:
        try:
            if not os.path.isfile(self._state_path):
                return
            import json

            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            clients = data.get("clients", {}) or {}
            auth_codes = data.get("auth_codes", {}) or {}
            access_tokens = data.get("access_tokens", {}) or {}
            refresh_tokens = data.get("refresh_tokens", {}) or {}
            self.clients = {cid: OAuthClientInformationFull(**obj) for cid, obj in clients.items()}
            self.auth_codes = {code: SDKAuthorizationCode(**obj) for code, obj in auth_codes.items()}
            self.access_tokens = {tok: SDKAccessToken(**obj) for tok, obj in access_tokens.items()}
            self.refresh_tokens = {tok: SDKRefreshToken(**obj) for tok, obj in refresh_tokens.items()}
            self._access_to_refresh_map = dict(data.get("access_to_refresh", {}) or {})
            self._refresh_to_access_map = dict(data.get("refresh_to_access", {}) or {})
        except Exception:
            # If load fails, start fresh
            self.clients = {}
            self.auth_codes = {}
            self.access_tokens = {}
            self.refresh_tokens = {}
            self._access_to_refresh_map = {}
            self._refresh_to_access_map = {}

    # Mutating operations: persist after calling parent
    async def register_client(self, client_info: OAuthClientInformationFull) -> None:  # type: ignore[override]
        await super().register_client(client_info)
        self._save_state()

    async def authorize(self, client: OAuthClientInformationFull, params):  # type: ignore[override]
        redirect = await super().authorize(client, params)
        self._save_state()
        return redirect

    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code):  # type: ignore[override]
        token = await super().exchange_authorization_code(client, authorization_code)
        self._save_state()
        return token

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token, scopes):  # type: ignore[override]
        token = await super().exchange_refresh_token(client, refresh_token, scopes)
        self._save_state()
        return token

    async def revoke_token(self, token):  # type: ignore[override]
        await super().revoke_token(token)
        self._save_state()

    async def load_access_token(self, token: str):  # type: ignore[override]
        at = await super().load_access_token(token)
        # In case load removed expired tokens
        self._save_state()
        return at


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Run an MCP server exposing all tools discovered under extensions/")
    parser.add_argument("--tool-root", default=None, help="Optional custom root directory to scan for *_tool.py (defaults to extensions/)")
    parser.add_argument("--name", default="Luna Extensions", help="MCP server name")
    parser.add_argument("--transport", choices=["sse", "stdio"], default="sse", help="Transport protocol")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE")
    parser.add_argument("--port", type=int, default=8060, help="Port for SSE")
    # Built-in auth options
    parser.add_argument("--auth", choices=["none", "inmemory", "jwt", "static"], default=os.getenv("MCP_AUTH", "none"), help="Enable built-in auth provider")
    parser.add_argument("--public-base-url", default=os.getenv("PUBLIC_BASE_URL"), help="Public base URL (e.g., https://xyz.ngrok-free.app) for OAuth metadata")
    parser.add_argument("--scopes", default=os.getenv("MCP_REQUIRED_SCOPES", ""), help="Space-separated required scopes for requests")
    # JWT verifier options (if --auth=jwt)
    parser.add_argument("--jwks-uri", default=os.getenv("MCP_JWKS_URI"), help="JWKS URI for JWT verification")
    parser.add_argument("--issuer", default=os.getenv("MCP_JWT_ISSUER"), help="Expected JWT issuer")
    parser.add_argument("--audience", default=os.getenv("MCP_JWT_AUDIENCE"), help="Expected audience (comma-separated) for JWT")
    # Static token options (if --auth=static)
    parser.add_argument("--static-token", default=os.getenv("MCP_STATIC_TOKEN"), help="Hardcoded bearer token to accept (store in .env as MCP_STATIC_TOKEN)")
    parser.add_argument("--static-client-id", default=os.getenv("MCP_STATIC_CLIENT_ID", "static-client"), help="Client ID associated with static token")
    parser.add_argument("--static-scopes", default=os.getenv("MCP_STATIC_SCOPES", ""), help="Space-separated scopes granted to the static token")
    # OAuth persistence (for --auth=inmemory)
    parser.add_argument("--oauth-state-file", default=os.getenv("OAUTH_STATE_FILE", os.path.join(PROJECT_ROOT, "logs", "oauth_state.json")), help="Path to persist OAuth state (clients/tokens)")
    args = parser.parse_args(argv)

    # Compute public base URL
    url_host = "localhost" if args.host == "0.0.0.0" else args.host
    inferred_base_url = f"http://{url_host}:{args.port}"
    base_url = (args.public_base_url or inferred_base_url).rstrip("/")

    # Configure auth provider
    auth_provider = None
    scopes_list = [s for s in (args.scopes or "").split(" ") if s]
    if args.auth == "inmemory":
        # Use file-backed provider to persist registrations and tokens
        auth_provider = FileBackedOAuthProvider(
            state_path=args.oauth_state_file,
            base_url=base_url,
            resource_server_url=base_url,
            required_scopes=scopes_list or None,
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=scopes_list or None,
                default_scopes=scopes_list or None,
            ),
            revocation_options=RevocationOptions(enabled=True),
        )
    elif args.auth == "jwt":
        aud_list = [a for a in (args.audience or "").split(",") if a.strip()]
        verifier = JWTVerifier(
            jwks_uri=args.jwks_uri,
            issuer=args.issuer,
            audience=aud_list or None,
            required_scopes=scopes_list or None,
            resource_server_url=base_url,
        )
        # Advertise the issuer as the authorization server
        if args.issuer:
            auth_provider = RemoteAuthProvider(
                token_verifier=verifier,
                authorization_servers=[args.issuer],
                resource_server_url=base_url,
            )
        else:
            auth_provider = verifier  # Fallback to pure verifier without metadata
    elif args.auth == "static":
        token = (args.static_token or "").strip()
        if not token:
            raise SystemExit("--static-token (or MCP_STATIC_TOKEN) is required when --auth=static")
        static_scopes = [s for s in (args.static_scopes or "").split(" ") if s]
        token_map: Dict[str, Dict[str, Any]] = {
            token: {
                "client_id": args.static_client_id,
                "scopes": static_scopes,
            }
        }
        auth_provider = StaticTokenVerifier(tokens=token_map, required_scopes=scopes_list or None)

    mcp = FastMCP(args.name, auth=auth_provider)

    tools = _load_tools(args.tool_root)
    registered = _register_tools(mcp, tools)

    if args.transport == "sse":
        url = f"http://{url_host}:{args.port}/sse"
        print(f"[MCP] {args.name}: {registered} tools registered. Serving via SSE at {url}")
        if auth_provider is not None:
            print(f"[MCP] Auth provider enabled. Resource URL: {base_url}")
            # Only OAuth providers have metadata endpoints
            if args.auth in ("inmemory", "jwt"):
                print(f"[MCP] OAuth metadata: {base_url}/.well-known/oauth-authorization-server")
                print(f"[MCP] Protected resource metadata: {base_url}/.well-known/oauth-protected-resource")
            elif args.auth == "static":
                print("[MCP] Static token auth enabled. No OAuth endpoints exposed.")
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        print(f"[MCP] {args.name}: {registered} tools registered. Serving via STDIO")
        mcp.run(transport="stdio")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


