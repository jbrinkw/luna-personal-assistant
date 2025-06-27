"""Run the ChefByte MCP tool server."""

from mcp_tools import mcp  # FastMCP instance
import mcp_tools.push_tools  # noqa: F401 - register tools
import mcp_tools.pull_tools  # noqa: F401 - register tools
import mcp_tools.action_tools  # noqa: F401 - register tools

if __name__ == "__main__":
    # Run an HTTP server on localhost for testing
    mcp.run(transport="http", port=8000)

