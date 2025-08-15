#!/usr/bin/env python3
"""
Home Assistant MCP Server
All-in-one MCP server with Home Assistant device control tools
"""

import requests
import os
import json
from typing import Optional
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create MCP server instance
mcp = FastMCP("Home Assistant Control Tools")

# Configuration
HA_URL = os.getenv("HA_URL", "http://192.168.0.216:8123")
HA_TOKEN = os.getenv("HA_TOKEN")

def get_headers():
    """Get headers for Home Assistant API requests"""
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }

def check_token():
    """Check if HA_TOKEN is configured"""
    if not HA_TOKEN:
        return False, "Error: HA_TOKEN environment variable not set!"
    return True, None

def HA_GET_devices() -> str:
    """Get list of all available Home Assistant devices and their current states.
    
    Returns devices with their entity IDs. Use the entity_id values with other tools."""
    try:
        token_ok, error = check_token()
        if not token_ok:
            return error
        
        # Get all states from Home Assistant
        url = f"{HA_URL}/api/states"
        headers = get_headers()
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        states = response.json()
        
        # Format the output nicely
        devices = []
        for state in states:
            if state['entity_id'].startswith(('light.', 'switch.', 'fan.', 'media_player.')):
                devices.append({
                    'entity_id': state['entity_id'],
                    'state': state['state'],
                    'domain': state['entity_id'].split('.')[0],
                    'friendly_name': state['attributes'].get('friendly_name', state['entity_id'])
                })
        
        return json.dumps(devices, indent=2)
        
    except Exception as e:
        return f"Error listing devices: {str(e)}"

def HA_GET_entity_status(entity_id: str) -> str:
    """Get status of a specific Home Assistant entity by entity ID.
    
    Use entity IDs like 'light.living_room' or 'switch.kitchen'.
    Use list_devices() first to see available entity IDs."""
    try:
        token_ok, error = check_token()
        if not token_ok:
            return error
        
        # Get specific entity state from Home Assistant
        url = f"{HA_URL}/api/states/{entity_id}"
        headers = get_headers()
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return f"Entity '{entity_id}' not found"
        
        response.raise_for_status()
        state = response.json()
        
        return json.dumps({
            'entity_id': state['entity_id'],
            'state': state['state'],
            'attributes': state['attributes']
        }, indent=2)
        
    except Exception as e:
        return f"Error getting entity status: {str(e)}"

def HA_ACTION_turn_entity_on(entity_id: str) -> str:
    """Turn on a specific Home Assistant entity by entity ID.
    
    Use entity IDs like 'light.living_room' or 'switch.kitchen'.
    Use list_devices() first to see available entity IDs."""
    try:
        token_ok, error = check_token()
        if not token_ok:
            return error
        
        # Determine the correct service based on domain
        domain = entity_id.split('.')[0]
        service_url = f"{HA_URL}/api/services/{domain}/turn_on"
        headers = get_headers()
        
        # Call the turn_on service
        service_data = {"entity_id": entity_id}
        response = requests.post(service_url, headers=headers, json=service_data, timeout=10)
        response.raise_for_status()
        
        return f"Successfully turned on '{entity_id}'"
        
    except Exception as e:
        return f"Error turning on {entity_id}: {str(e)}"

def HA_ACTION_turn_entity_off(entity_id: str) -> str:
    """Turn off a specific Home Assistant entity by entity ID.
    
    Use entity IDs like 'light.living_room' or 'switch.kitchen'.
    Use list_devices() first to see available entity IDs."""
    try:
        token_ok, error = check_token()
        if not token_ok:
            return error
        
        # Determine the correct service based on domain
        domain = entity_id.split('.')[0]
        service_url = f"{HA_URL}/api/services/{domain}/turn_off"
        headers = get_headers()
        
        # Call the turn_off service
        service_data = {"entity_id": entity_id}
        response = requests.post(service_url, headers=headers, json=service_data, timeout=10)
        response.raise_for_status()
        
        return f"Successfully turned off '{entity_id}'"
        
    except Exception as e:
        return f"Error turning off {entity_id}: {str(e)}"

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
        # Check if required environment variables are set
        if not os.getenv('HA_TOKEN'):
            print("❌ HA_TOKEN environment variable not set!")
            return
        
        # Run tests
        test_all_tools()
    else:
        # Run MCP server
        url = f"http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/sse"
        print(f"[HomeAssistant] Running MCP server via SSE at {url}")
        print(f"Available tools: HA_GET_devices, HA_GET_entity_status, HA_ACTION_turn_entity_on, HA_ACTION_turn_entity_off")
        print(f"All tools now use entity IDs directly (like 'light.living_room')")
        
        # Register tools (no decorator) so local tests can call functions directly
        mcp.tool(HA_GET_devices)
        mcp.tool(HA_GET_entity_status)
        mcp.tool(HA_ACTION_turn_entity_on)
        mcp.tool(HA_ACTION_turn_entity_off)
        
        mcp.run(transport="sse", host=args.host, port=args.port)

if __name__ == "__main__":
    main()