from typing import Callable, Any, Optional
from fastapi import FastAPI, Request
import uvicorn

class MCPServer:
    """Minimal implementation of a server exposing functions as MCP endpoints."""

    def __init__(self, name: str):
        self.app = FastAPI(title=name)

    def register(self, func: Callable, path: Optional[str] = None) -> Callable:
        """Register a function as a POST endpoint returning JSON."""
        endpoint_path = f"/{path or func.__name__}"

        async def endpoint(request: Request) -> dict:
            try:
                data = await request.json()
            except Exception:
                data = {}
            result = func(**data) if data else func()
            return {"result": result}

        self.app.post(endpoint_path)(endpoint)
        return func

    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        uvicorn.run(self.app, host=host, port=port)
