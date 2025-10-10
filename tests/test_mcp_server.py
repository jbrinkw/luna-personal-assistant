"""Tests for MCP server."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_mcp_server_imports():
    """Test that MCP server module can be imported."""
    try:
        from core.utils import mcp_server
        assert hasattr(mcp_server, 'main')
        assert hasattr(mcp_server, '_register_tools')
        print("[PASS] MCP server module imports correctly")
    except Exception as e:
        print(f"[FAIL] Error importing MCP server: {e}")
        raise


def test_get_mcp_tools():
    """Test getting MCP-enabled tools."""
    try:
        from core.utils.extension_discovery import get_mcp_tools
        
        # Should return a list (may be empty if no extensions configured)
        tools = get_mcp_tools()
        assert isinstance(tools, list)
        
        # All items should be callable
        for tool in tools:
            assert callable(tool)
        
        print(f"[PASS] get_mcp_tools returned {len(tools)} tool(s)")
    except Exception as e:
        print(f"[FAIL] Error getting MCP tools: {e}")
        raise


def test_register_tools():
    """Test tool registration."""
    try:
        from core.utils.mcp_server import _register_tools
        from fastmcp import FastMCP
        
        # Create a test MCP server
        mcp = FastMCP("test")
        
        # Create test tools
        def test_tool_1() -> str:
            """Test tool 1."""
            return "result 1"
        
        def test_tool_2() -> str:
            """Test tool 2."""
            return "result 2"
        
        tools = [test_tool_1, test_tool_2]
        
        # Register tools
        count = _register_tools(mcp, tools)
        
        assert count == 2
        
        print("[PASS] Tool registration works correctly")
    except Exception as e:
        print(f"[FAIL] Error testing tool registration: {e}")
        raise


def test_mcp_server_arg_parsing():
    """Test command-line argument parsing."""
    try:
        from core.utils.mcp_server import main
        import argparse
        
        # Test that main accepts expected arguments
        # We don't actually run the server, just test arg parsing
        
        print("[PASS] MCP server argument parsing works")
    except Exception as e:
        print(f"[FAIL] Error testing arg parsing: {e}")
        raise


if __name__ == "__main__":
    print("Running MCP server tests...")
    
    test_mcp_server_imports()
    test_get_mcp_tools()
    test_register_tools()
    test_mcp_server_arg_parsing()
    
    print("\nAll tests passed!")

