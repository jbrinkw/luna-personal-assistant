"""Client-only test script that connects to a remote ChefByte MCP server.

Assumes the aggregated server is running on 192.168.1.234:8000 over
SSE (URL ends with /sse). Adjust the URL or tool name as needed.
"""

import asyncio
from fastmcp import Client

SERVER_URL = "http://192.168.1.234:8000/sse"


def main() -> None:
    asyncio.run(run_client())


async def run_client():
    print(f"Connecting to MCP server at {SERVER_URL} ...")
    async with Client(SERVER_URL) as client:
        tools = await client.list_tools()
        print("Tools on server:", [t.name for t in tools])

        # Example: call the inventory context tool (namespaced under pull)
        if any(t.name == "pull_get_inventory_context" for t in tools):
            result = await client.call_tool("pull_get_inventory_context")
            if result:
                first_part = result[0]
                text = getattr(first_part, "text", str(first_part))
                print("Inventory context:\n", text)
        else:
            print("Tool 'pull_get_inventory_context' not found on remote server.")


if __name__ == "__main__":
    main()

