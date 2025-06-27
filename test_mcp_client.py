"""Simple client test for the MCP server."""

import asyncio
import subprocess
import sys
import time

from fastmcp import Client

SERVER_SCRIPT = "mcp_server.py"
# FastMCP defaults to serving under /mcp when using HTTP transport
SERVER_URL = "http://localhost:8000/mcp"

async def call_inventory():
    async with Client(SERVER_URL) as client:
        tools = await client.list_tools()
        print("Tools on server:", [t.name for t in tools])
        result = await client.call_tool("get_inventory_context")
        text = result[0].text if result else "(no content)"
        print("Inventory context:\n", text)


def main():
    server = subprocess.Popen([sys.executable, SERVER_SCRIPT])
    try:
        time.sleep(2)  # wait for server to start
        asyncio.run(call_inventory())
    finally:
        server.terminate()
        server.wait()

if __name__ == "__main__":
    main()

