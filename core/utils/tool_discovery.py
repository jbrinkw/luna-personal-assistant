#!/usr/bin/env python3
"""
Tool Discovery - Centralized tool loading from all sources
Loads tools from local extensions, remote MCP servers, and future sources
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Callable, Union, Optional

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.utils.extension_discovery import discover_extensions, get_mcp_tools


class MCPRemoteTool:
    """Wrapper for remote MCP tools that implements callable interface."""
    
    def __init__(self, server_id: str, tool_name: str, tool_config: Dict[str, Any], session_manager):
        """Initialize remote tool wrapper.
        
        Args:
            server_id: Remote MCP server identifier
            tool_name: Tool name
            tool_config: Tool configuration (docstring, schemas, etc.)
            session_manager: RemoteMCPSessionManager instance
        """
        self._server_id = server_id
        self._tool_name = tool_name
        self._tool_config = tool_config
        self._session_manager = session_manager
        
        # Set attributes for tool registration
        self.__name__ = tool_name
        self.__doc__ = tool_config.get('docstring', f"Remote MCP tool: {tool_name}")
        
        # Store input schema for potential use
        self.input_schema = tool_config.get('input_schema')
        self.output_schema = tool_config.get('output_schema')
    
    def __call__(self, **kwargs) -> str:
        """Call the remote tool.
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            Tool result as string
        """
        if not self._session_manager:
            raise RuntimeError(f"No session manager available for remote tool {self._tool_name}")
        
        return self._session_manager.call_tool(self._server_id, self._tool_name, kwargs)
    
    def __repr__(self):
        return f"<MCPRemoteTool {self._server_id}.{self._tool_name}>"


def get_all_tools() -> Dict[str, Any]:
    """Get tools from all sources, grouped by type.
    
    Returns:
        {
            "extensions": [
                {
                    "name": "automation_memory",
                    "enabled": true,
                    "tools": [
                        {
                            "name": "MEMORY_CREATE",
                            "enabled_in_mcp": true,
                            "passthrough": false
                        }
                    ]
                }
            ],
            "remote_mcp_servers": [
                {
                    "server_id": "mcp.exa.ai/mcp",
                    "enabled": true,
                    "tool_count": 2,
                    "tools": {
                        "web_search_exa": {
                            "enabled": true,
                            "docstring": "...",
                            "input_schema": {...}
                        }
                    }
                }
            ]
        }
    """
    # Load master_config
    master_config_path = PROJECT_ROOT / 'core' / 'master_config.json'
    master_config = {}
    try:
        if master_config_path.exists():
            with open(master_config_path, 'r') as f:
                master_config = json.load(f)
    except Exception as e:
        print(f"[ToolDiscovery] Warning: Failed to load master_config: {e}", flush=True)
    
    # Get local extension tools
    extensions_data = []
    discovered_exts = discover_extensions()
    
    for ext in discovered_exts:
        ext_name = ext.get('name', '')
        tools = ext.get('tools', [])
        tool_configs = ext.get('tool_configs', {})
        
        # Get enabled status from master_config
        ext_config = master_config.get('extensions', {}).get(ext_name, {})
        ext_enabled = ext_config.get('enabled', True)
        
        # Build tool list with configs
        tools_list = []
        for tool in tools:
            tool_name = getattr(tool, '__name__', 'unknown')
            tool_config = tool_configs.get(tool_name, {})
            
            # Also check master_config.tool_configs
            master_tool_config = master_config.get('tool_configs', {}).get(tool_name, {})
            
            # Merge configs (master_config takes precedence)
            merged_config = {**tool_config, **master_tool_config}
            
            tools_list.append({
                'name': tool_name,
                'enabled_in_mcp': merged_config.get('enabled_in_mcp', False),
                'passthrough': merged_config.get('passthrough', False),
                'docstring': getattr(tool, '__doc__', '')
            })
        
        if tools_list:  # Only include extensions with tools
            extensions_data.append({
                'name': ext_name,
                'enabled': ext_enabled,
                'tool_count': len(tools_list),
                'tools': tools_list
            })
    
    # Get remote MCP servers
    remote_servers_data = []
    remote_servers = master_config.get('remote_mcp_servers', {})
    
    for server_id, server_config in remote_servers.items():
        remote_servers_data.append({
            'server_id': server_id,
            'enabled': server_config.get('enabled', True),
            'tool_count': server_config.get('tool_count', 0),
            'url': server_config.get('url', ''),
            'tools': server_config.get('tools', {})
        })
    
    return {
        'extensions': extensions_data,
        'remote_mcp_servers': remote_servers_data
    }


def get_mcp_enabled_tools(session_manager=None) -> List[Union[Callable, MCPRemoteTool]]:
    """Get all tools enabled for MCP exposure.
    
    Combines:
    - Local extension tools (where enabled_in_mcp=true)
    - Remote MCP tools (wrapped in MCPRemoteTool)
    
    Args:
        session_manager: Optional RemoteMCPSessionManager instance for remote tools
        
    Returns:
        List of tools (mix of callables and MCPRemoteTool instances)
    """
    tools = []
    
    # Get local extension tools
    local_tools = get_mcp_tools()
    tools.extend(local_tools)
    
    # Get remote MCP tools if session manager provided
    if session_manager:
        # Load master_config
        master_config_path = PROJECT_ROOT / 'core' / 'master_config.json'
        try:
            if master_config_path.exists():
                with open(master_config_path, 'r') as f:
                    master_config = json.load(f)
                    
                remote_servers = master_config.get('remote_mcp_servers', {})
                
                for server_id, server_config in remote_servers.items():
                    # Skip disabled servers
                    if not server_config.get('enabled', True):
                        continue
                    
                    # Skip servers with no active session
                    if not session_manager.has_session(server_id):
                        continue
                    
                    # Add enabled tools from this server
                    server_tools = server_config.get('tools', {})
                    for tool_name, tool_config in server_tools.items():
                        # Skip disabled tools
                        if not tool_config.get('enabled', True):
                            continue
                        
                        # Wrap remote tool
                        remote_tool = MCPRemoteTool(
                            server_id=server_id,
                            tool_name=tool_name,
                            tool_config=tool_config,
                            session_manager=session_manager
                        )
                        tools.append(remote_tool)
        except Exception as e:
            print(f"[ToolDiscovery] Warning: Failed to load remote MCP tools: {e}", flush=True)
    
    return tools


def get_tool_count_by_source() -> Dict[str, int]:
    """Get count of tools by source.
    
    Returns:
        {
            "local_extensions": int,
            "remote_mcp_servers": int,
            "total": int
        }
    """
    all_tools = get_all_tools()
    
    local_count = sum(ext['tool_count'] for ext in all_tools.get('extensions', []))
    remote_count = sum(server['tool_count'] for server in all_tools.get('remote_mcp_servers', []))
    
    return {
        'local_extensions': local_count,
        'remote_mcp_servers': remote_count,
        'total': local_count + remote_count
    }

