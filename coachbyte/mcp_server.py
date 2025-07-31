"""Run the CoachByte MCP server exposing all workout tools."""

from fastmcp import FastMCP
import tools
from agents.tool import FunctionTool as AgentsFunctionTool
from agents.tool_context import ToolContext
import json
import inspect
import uuid

mcp = FastMCP("CoachByte Tools")

def convert_tool(tool_obj: AgentsFunctionTool):
    """Convert an OpenAI Agents FunctionTool to a FastMCP compatible callable."""
    schema = tool_obj.params_json_schema
    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    async def wrapper(**kwargs):
        data = kwargs
        call_id = uuid.uuid4().hex
        ctx = ToolContext(context=None, tool_name=tool_obj.name, tool_call_id=call_id)
        result = tool_obj.on_invoke_tool(ctx, json.dumps(data))
        if inspect.isawaitable(result):
            result = await result
        return result

    # Build a signature matching the tool schema
    parameters = []
    for name, prop in props.items():
        default = inspect._empty if name in required else None
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
            )
        )
    wrapper.__signature__ = inspect.Signature(parameters=parameters)
    wrapper.__name__ = tool_obj.name
    wrapper.__doc__ = tool_obj.description
    return wrapper

for name in getattr(tools, "__all__", []):
    tool_obj = getattr(tools, name)
    if isinstance(tool_obj, AgentsFunctionTool):
        mcp.tool(convert_tool(tool_obj))
    else:
        mcp.tool(tool_obj)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the aggregated CoachByte MCP server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host (default 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8100,
        help="Port (default 8100)",
    )
    args = parser.parse_args()

    url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
    print(f"[CoachByte] Running via SSE at {url}")

    mcp.run(transport="sse", host=args.host, port=args.port)
