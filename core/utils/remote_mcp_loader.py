#!/usr/bin/env python3
"""
Remote MCP Loader - Load tools from remote Smithery MCP servers
"""
import asyncio
import json
from typing import Dict, Any, Optional

try:
    from mcp import ClientSession, types
    from mcp.client.streamable_http import streamablehttp_client
except ImportError as e:
    raise ImportError(
        "mcp library required for remote MCP servers. Install with: pip install mcp"
    ) from e


def extract_server_id_from_url(url: str) -> str:
    """Extract server ID from URL.
    
    Extracts the part between '//' and 'api_key=' (or end of path if no api_key).
    Example: https://mcp.exa.ai/mcp?api_key=xyz -> mcp.exa.ai/mcp
    
    Args:
        url: MCP server URL
        
    Returns:
        Server identifier extracted from URL
    """
    try:
        # Remove protocol
        if '://' in url:
            url_without_protocol = url.split('://', 1)[1]
        else:
            url_without_protocol = url
        
        # Extract part before api_key parameter
        if 'api_key=' in url_without_protocol:
            server_id = url_without_protocol.split('api_key=')[0].strip('?&/')
        else:
            # No api_key, just remove query params
            server_id = url_without_protocol.split('?')[0].strip('/')
        
        return server_id
    except Exception:
        # Fallback: use hash of URL
        import hashlib
        return f"server-{hashlib.md5(url.encode()).hexdigest()[:12]}"


async def load_mcp_server(url: str) -> Dict[str, Any]:
    """Connect to MCP server and load tools.
    
    Args:
        url: MCP server URL (e.g., Smithery MCP URL with credentials)
        
    Returns:
        Dictionary with server metadata and tools:
        {
            "server_id": str,  # From MCP initialize or extracted from URL
            "url": str,
            "tool_count": int,
            "tools": {
                "tool_name": {
                    "enabled": bool,
                    "docstring": str,
                    "input_schema": dict,
                    "output_schema": dict
                }
            }
        }
    """
    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                # Initialize and get server info
                init_result = await session.initialize()
                
                # Extract server name from initialize response
                server_id = None
                if init_result and hasattr(init_result, 'serverInfo') and init_result.serverInfo:
                    server_name = getattr(init_result.serverInfo, 'name', None)
                    if server_name:
                        server_id = server_name
                
                # Fallback to URL extraction if no server name
                if not server_id:
                    server_id = extract_server_id_from_url(url)
                
                # List tools
                tools_response = await session.list_tools()
                tools = tools_response.tools
                
                # Build tool cache
                tool_cache = {}
                for tool in tools:
                    tool_cache[tool.name] = {
                        "enabled": True,  # Default to enabled for new tools
                        "docstring": (tool.description or "").strip(),
                        "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else None,
                        "output_schema": tool.outputSchema if hasattr(tool, 'outputSchema') else None,
                    }
                
                return {
                    "server_id": server_id,
                    "url": url,
                    "tool_count": len(tools),
                    "tools": tool_cache
                }
    except Exception as e:
        raise RuntimeError(f"Failed to connect to MCP server: {e}") from e


def add_or_update_server(master_config: Dict[str, Any], server_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add or update a remote MCP server in master_config.
    
    Preserves enabled states for existing servers and tools.
    
    Args:
        master_config: Master configuration dictionary
        server_data: Server data from load_mcp_server()
        
    Returns:
        Updated server entry
    """
    server_id = server_data['server_id']
    
    # Initialize remote_mcp_servers if not present
    if 'remote_mcp_servers' not in master_config:
        master_config['remote_mcp_servers'] = {}
    
    # Check if server already exists
    existing_server = master_config['remote_mcp_servers'].get(server_id)
    
    # Preserve enabled states
    if existing_server:
        # Preserve server-level enabled state
        enabled = existing_server.get('enabled', True)
        
        # Preserve tool-level enabled states
        existing_tools = existing_server.get('tools', {})
        for tool_name, tool_data in server_data['tools'].items():
            if tool_name in existing_tools:
                # Keep existing enabled state
                tool_data['enabled'] = existing_tools[tool_name].get('enabled', True)
    else:
        # New server, default to enabled
        enabled = True
    
    # Create server entry
    server_entry = {
        "server_id": server_id,
        "url": server_data['url'],
        "enabled": enabled,
        "tool_count": server_data['tool_count'],
        "tools": server_data['tools']
    }
    
    # Add to master config
    master_config['remote_mcp_servers'][server_id] = server_entry
    
    return server_entry


async def async_add_or_update_server_from_url(master_config: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Load MCP server from URL and add/update in master_config.
    
    This is the main entry point for adding remote MCP servers.
    
    Args:
        master_config: Master configuration dictionary
        url: MCP server URL
        
    Returns:
        Updated server entry
    """
    # Load server data
    server_data = await load_mcp_server(url)
    
    # Add or update in config
    server_entry = add_or_update_server(master_config, server_data)
    
    return server_entry


def remove_server(master_config: Dict[str, Any], server_id: str) -> bool:
    """Remove a remote MCP server from master_config.
    
    Args:
        master_config: Master configuration dictionary
        server_id: Server identifier
        
    Returns:
        True if server was removed, False if not found
    """
    if 'remote_mcp_servers' not in master_config:
        return False
    
    if server_id in master_config['remote_mcp_servers']:
        del master_config['remote_mcp_servers'][server_id]
        return True
    
    return False

