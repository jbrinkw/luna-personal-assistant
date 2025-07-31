"""Run the CoachByte MCP server exposing all workout tools."""

from fastmcp import FastMCP
import tools
from agents.tool import FunctionTool as AgentsFunctionTool
from agents.tool_context import ToolContext
import json
import inspect

mcp = FastMCP("CoachByte Tools")

def convert_tool(tool_obj: AgentsFunctionTool):
    schema = tool_obj.params_json_schema
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    arg_defs = []
    data_items = []
    for arg in props:
        if arg in required:
            arg_defs.append(arg)
        else:
            arg_defs.append(f"{arg}=None")
        data_items.append(f"        '{arg}': {arg}")
    args_code = ", ".join(arg_defs)
    data_code = ",\n".join(data_items)
    func_src = f"async def wrapper({args_code}):\n" \
        f"    data = {{\n{data_code}\n    }}\n" \
        "    data = {k: v for k, v in data.items() if v is not None}\n" \
        "    ctx = ToolContext(context=None, tool_name=tool_obj.name, tool_call_id='fastmcp')\n" \
        "    return await tool_obj.on_invoke_tool(ctx, json.dumps(data))"
    ns = {'ToolContext': ToolContext, 'tool_obj': tool_obj, 'json': json}
    exec(func_src, ns)
    wrapped = ns['wrapper']
    wrapped.__name__ = tool_obj.name
    wrapped.__doc__ = tool_obj.description
    return wrapped

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
