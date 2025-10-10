"""Tests for extension discovery module."""
import os
import sys
import tempfile
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.utils.extension_discovery import discover_extensions, build_all_light_schema, get_mcp_tools


def test_discover_extensions_empty_directory():
    """Test discovery with empty/non-existent directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        extensions = discover_extensions(tmpdir)
        assert extensions == []


def test_discover_extensions_with_tools():
    """Test discovery with a valid extension."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create extension structure
        ext_dir = Path(tmpdir) / "test_extension"
        tools_dir = ext_dir / "tools"
        tools_dir.mkdir(parents=True)
        
        # Create config.json
        config = {"name": "test_extension", "required_secrets": ["TEST_KEY"]}
        with open(ext_dir / "config.json", "w") as f:
            json.dump(config, f)
        
        # Create tool_config.json
        tool_config = {
            "TEST_get_data": {
                "enabled_in_mcp": True,
                "passthrough": False
            }
        }
        with open(tools_dir / "tool_config.json", "w") as f:
            json.dump(tool_config, f)
        
        # Create tools file
        tools_file = tools_dir / "test_tools.py"
        tools_file.write_text('''
SYSTEM_PROMPT = "Test system prompt"

def TEST_get_data(query: str) -> str:
    """Get test data.
    Example Prompt: get test data for query
    Example Response: {"result": "data"}
    Example Args: {"query": "test"}
    """
    return f"Test result for {query}"

TOOLS = [TEST_get_data]
''')
        
        # Discover extensions
        extensions = discover_extensions(tmpdir)
        
        assert len(extensions) == 1
        assert extensions[0]['name'] == 'test_extension'
        assert len(extensions[0]['tools']) == 1
        assert extensions[0]['system_prompt'] == 'Test system prompt'
        assert 'TEST_get_data' in extensions[0]['tool_configs']


def test_get_mcp_tools():
    """Test filtering tools enabled for MCP."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create extension with MCP-enabled and disabled tools
        ext_dir = Path(tmpdir) / "test_ext"
        tools_dir = ext_dir / "tools"
        tools_dir.mkdir(parents=True)
        
        # Tool config with mixed MCP settings
        tool_config = {
            "ENABLED_tool": {"enabled_in_mcp": True},
            "DISABLED_tool": {"enabled_in_mcp": False}
        }
        with open(tools_dir / "tool_config.json", "w") as f:
            json.dump(tool_config, f)
        
        # Create tools
        tools_file = tools_dir / "mixed_tools.py"
        tools_file.write_text('''
def ENABLED_tool() -> str:
    """MCP enabled tool."""
    return "enabled"

def DISABLED_tool() -> str:
    """MCP disabled tool."""
    return "disabled"

TOOLS = [ENABLED_tool, DISABLED_tool]
''')
        
        # Mock discover_extensions to use our temp directory
        import core.utils.extension_discovery as discovery_module
        original_discover = discovery_module.discover_extensions
        discovery_module.discover_extensions = lambda root=None: discover_extensions(tmpdir)
        
        try:
            mcp_tools = get_mcp_tools()
            tool_names = [t.__name__ for t in mcp_tools]
            
            assert 'ENABLED_tool' in tool_names
            assert 'DISABLED_tool' not in tool_names
        finally:
            discovery_module.discover_extensions = original_discover


def test_build_all_light_schema():
    """Test schema building."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_dir = Path(tmpdir) / "schema_test"
        tools_dir = ext_dir / "tools"
        tools_dir.mkdir(parents=True)
        
        tools_file = tools_dir / "schema_tools.py"
        tools_file.write_text('''
def SCHEMA_test_function(name: str, count: int) -> str:
    """Test function with typed params."""
    return f"Result: {name} x {count}"

TOOLS = [SCHEMA_test_function]
''')
        
        # Mock discover
        import core.utils.extension_discovery as discovery_module
        original_discover = discovery_module.discover_extensions
        discovery_module.discover_extensions = lambda root=None: discover_extensions(tmpdir)
        
        try:
            schema = build_all_light_schema()
            assert 'SCHEMA_test_function' in schema
            assert 'name' in schema
            assert 'count' in schema
        finally:
            discovery_module.discover_extensions = original_discover


if __name__ == "__main__":
    print("Running extension discovery tests...")
    test_discover_extensions_empty_directory()
    print("[PASS] Empty directory test passed")
    
    test_discover_extensions_with_tools()
    print("[PASS] Extension discovery test passed")
    
    test_get_mcp_tools()
    print("[PASS] MCP tools filtering test passed")
    
    test_build_all_light_schema()
    print("[PASS] Schema building test passed")
    
    print("\nAll tests passed!")

