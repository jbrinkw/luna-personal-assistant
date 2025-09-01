#!/usr/bin/env python3
"""
Home Assistant MCP Server
All-in-one MCP server with Home Assistant device control tools.

This now imports local tool functions (no decorators) from
`homeassistant_local_tools.py` and registers them with MCP so behavior
is identical for both local and MCP-based use.
"""

import os
from fastmcp import FastMCP
from dotenv import load_dotenv
from core.integrations.homeassistant_local_tools import (
    HA_GET_devices,
    HA_GET_entity_status,
    HA_ACTION_turn_entity_on,
    HA_ACTION_turn_entity_off,
)

# Load environment variables from .env file
load_dotenv()

# Create MCP server instance
mcp = FastMCP("Home Assistant Control Tools")

def _register_tools(mcp: FastMCP) -> None:
    mcp.tool(HA_GET_devices)
    mcp.tool(HA_GET_entity_status)
    mcp.tool(HA_ACTION_turn_entity_on)
    mcp.tool(HA_ACTION_turn_entity_off)

# Test function (not an MCP tool)
def test_all_tools():
    """Test all the tools (for debugging purposes)"""
    print("🧪 Testing Home Assistant MCP Tools")
    print("=" * 50)
    
    # Test 1: List devices
    print("\n1️⃣ Testing HA_GET_devices()...")
    devices = HA_GET_devices()
    print(f"Devices: {devices}")
    
    # Test 2: Get entity status
    print("\n2️⃣ Testing HA_GET_entity_status('light.living_room')...")
    status = HA_GET_entity_status("light.living_room")
    print(f"Status: {status}")
    
    # Test 3: Turn entity on
    print("\n3️⃣ Testing HA_ACTION_turn_entity_on('light.living_room')...")
    on_result = HA_ACTION_turn_entity_on("light.living_room")
    print(f"Turn on result: {on_result}")
    
    # Wait a moment
    import time
    time.sleep(2)
    
    # Test 4: Turn entity off
    print("\n4️⃣ Testing HA_ACTION_turn_entity_off('light.living_room')...")
    off_result = HA_ACTION_turn_entity_off("light.living_room")
    print(f"Turn off result: {off_result}")
    
    print("\n✅ All tests completed!")

def main():
    """Main function for testing or running the server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the Home Assistant MCP server")
    parser.add_argument("--test", action="store_true", help="Run tests instead of server")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8051, help="Port (default 8051)")
    args = parser.parse_args()
    
    if args.test:
        if not os.getenv('HA_TOKEN'):
            print("❌ HA_TOKEN environment variable not set!")
            return
        # Import and execute local tests from local tools if desired
        print("HA tools available: HA_GET_devices, HA_GET_entity_status, HA_ACTION_turn_entity_on, HA_ACTION_turn_entity_off")
        print("Run with --host/--port to start MCP server.")
    else:
        url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
        print(f"[HomeAssistant] Running MCP server via SSE at {url}")
        print("Registering HomeAssistant local tools with MCP...")
        _register_tools(mcp)
        mcp.run(transport="sse", host=args.host, port=args.port)

if __name__ == "__main__":
    main()