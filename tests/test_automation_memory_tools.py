"""Tests for automation_memory tools."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_tools_import():
    """Test that automation_memory tools can be imported."""
    try:
        from extensions.automation_memory.tools import automation_memory_tools
        assert hasattr(automation_memory_tools, 'TOOLS')
        assert hasattr(automation_memory_tools, 'SYSTEM_PROMPT')
        print("[PASS] Automation memory tools import correctly")
    except Exception as e:
        print(f"[FAIL] Error importing tools: {e}")
        raise


def test_tools_list():
    """Test that TOOLS list contains expected functions."""
    try:
        from extensions.automation_memory.tools.automation_memory_tools import TOOLS
        
        assert isinstance(TOOLS, list)
        assert len(TOOLS) > 0
        
        # Check all tools are callable
        for tool in TOOLS:
            assert callable(tool)
        
        # Check expected tools exist
        tool_names = [t.__name__ for t in TOOLS]
        expected_tools = [
            "MEMORY_GET_all",
            "MEMORY_UPDATE_create",
            "FLOW_GET_all",
            "FLOW_ACTION_run",
            "SCHEDULE_GET_all",
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Expected tool {expected} not found"
        
        print(f"[PASS] Found {len(TOOLS)} tools with correct naming")
    except Exception as e:
        print(f"[FAIL] Error testing tools list: {e}")
        raise


def test_pydantic_models():
    """Test that Pydantic models are properly defined."""
    try:
        from extensions.automation_memory.tools.automation_memory_tools import (
            MEMORY_UPDATE_CreateArgs,
            FLOW_UPDATE_CreateArgs,
            SCHEDULE_UPDATE_CreateArgs
        )
        from pydantic import ValidationError
        
        # Test MEMORY_UPDATE_CreateArgs
        mem_args = MEMORY_UPDATE_CreateArgs(content="test memory")
        assert mem_args.content == "test memory"
        
        # Test validation failure
        try:
            MEMORY_UPDATE_CreateArgs()  # Missing required field
            assert False, "Should have raised validation error"
        except ValidationError:
            pass
        
        # Test FLOW_UPDATE_CreateArgs
        flow_args = FLOW_UPDATE_CreateArgs(
            call_name="test_flow",
            prompts=["prompt 1", "prompt 2"]
        )
        assert flow_args.call_name == "test_flow"
        assert flow_args.agent == "simple_agent"  # Default value
        
        # Test SCHEDULE_UPDATE_CreateArgs
        schedule_args = SCHEDULE_UPDATE_CreateArgs(
            time_of_day="09:00",
            days_of_week=[False, True, True, True, True, True, False],
            prompt="test prompt"
        )
        assert schedule_args.time_of_day == "09:00"
        assert schedule_args.enabled is True  # Default value
        
        print("[PASS] Pydantic models work correctly")
    except Exception as e:
        print(f"[FAIL] Error testing Pydantic models: {e}")
        raise


def test_tool_return_format():
    """Test that tools return (bool, str) tuples."""
    try:
        from extensions.automation_memory.tools.automation_memory_tools import (
            MEMORY_GET_all,
            FLOW_GET_all,
            SCHEDULE_GET_all
        )
        
        # These tools will fail without database, but should return proper format
        for tool in [MEMORY_GET_all, FLOW_GET_all, SCHEDULE_GET_all]:
            result = tool()
            assert isinstance(result, tuple), f"{tool.__name__} should return tuple"
            assert len(result) == 2, f"{tool.__name__} should return 2-tuple"
            assert isinstance(result[0], bool), f"{tool.__name__} first element should be bool"
            assert isinstance(result[1], str), f"{tool.__name__} second element should be str"
        
        print("[PASS] Tools return correct format (bool, str)")
    except Exception as e:
        print(f"[FAIL] Error testing tool return format: {e}")
        raise


def test_tool_docstrings():
    """Test that tools have proper docstrings with required sections."""
    try:
        from extensions.automation_memory.tools.automation_memory_tools import TOOLS
        
        required_sections = ["Example Prompt:", "Example Response:", "Example Args:"]
        
        for tool in TOOLS:
            doc = tool.__doc__ or ""
            
            # Check docstring exists
            assert doc.strip(), f"{tool.__name__} missing docstring"
            
            # Check required sections
            for section in required_sections:
                assert section in doc, f"{tool.__name__} missing '{section}' in docstring"
        
        print("[PASS] All tools have proper docstrings")
    except Exception as e:
        print(f"[FAIL] Error testing docstrings: {e}")
        raise


def test_system_prompt_exists():
    """Test that SYSTEM_PROMPT is defined."""
    try:
        from extensions.automation_memory.tools.automation_memory_tools import SYSTEM_PROMPT
        
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0
        assert "memories" in SYSTEM_PROMPT.lower()
        
        print("[PASS] SYSTEM_PROMPT is properly defined")
    except Exception as e:
        print(f"[FAIL] Error testing SYSTEM_PROMPT: {e}")
        raise


if __name__ == "__main__":
    print("Running automation_memory tools tests...")
    
    test_tools_import()
    test_tools_list()
    test_pydantic_models()
    test_tool_return_format()
    test_tool_docstrings()
    test_system_prompt_exists()
    
    print("\nAll tests passed!")

