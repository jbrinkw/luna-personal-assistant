"""
Authentication middleware helper for Luna extension services.

Provides simple API key validation for services that require public exposure
with authentication (similar to MCP server APIKeyMiddleware pattern).
"""
import os
import secrets
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Simple bearer-token middleware for API key protected extension services.

    Usage in FastAPI app:
        from core.utils.service_auth import APIKeyMiddleware

        api_key = os.getenv("SERVICE_COACHBYTE_API_API_KEY")
        app.add_middleware(APIKeyMiddleware, api_key=api_key)

    Clients must send:
        Authorization: Bearer <api_key>
    or:
        X-API-Key: <api_key>
    """

    def __init__(self, app, api_key: str):
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next: Callable):
        # Allow OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check Authorization header (Bearer token)
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        else:
            # Fallback to X-API-Key header
            token = request.headers.get("x-api-key", "")

        # Validate token
        if token and secrets.compare_digest(token, self._api_key):
            return await call_next(request)

        return JSONResponse(
            {"error": "unauthorized", "detail": "Missing or invalid API key"},
            status_code=401,
        )


def get_service_api_key(extension_name: str, service_name: str) -> Optional[str]:
    """
    Get the API key for a service from environment variables.

    Args:
        extension_name: Name of the extension (e.g., "coachbyte")
        service_name: Name of the service (e.g., "api")

    Returns:
        API key string or None if not found

    Example:
        api_key = get_service_api_key("coachbyte", "api")
        if not api_key:
            raise RuntimeError("SERVICE_COACHBYTE_API_API_KEY not found in environment")
    """
    import re
    safe_ext = re.sub(r'[^A-Za-z0-9]+', '_', extension_name).upper().strip('_')
    safe_svc = re.sub(r'[^A-Za-z0-9]+', '_', service_name).upper().strip('_')
    env_key = f"SERVICE_{safe_ext}_{safe_svc}_API_KEY"
    return os.getenv(env_key)
