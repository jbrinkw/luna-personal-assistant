"""Tests for passthrough agent module."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_agent_imports():
    """Test that passthrough agent module can be imported."""
    try:
        from core.agents.passthrough_agent import agent
        assert hasattr(agent, 'run_agent')
        assert hasattr(agent, 'run_agent_stream')
        assert hasattr(agent, 'initialize_runtime')
        print("[PASS] Passthrough agent module imports correctly")
    except Exception as e:
        print(f"[FAIL] Error importing passthrough agent: {e}")
        raise


def test_agent_models():
    """Test that Pydantic models are properly defined."""
    try:
        from core.agents.passthrough_agent.agent import (
            AgentResult, ToolTrace, Timing, ToolResult,
            PlannedToolCall, ToolCallOptions, PlannerStep
        )
        
        # Test AgentResult
        result = AgentResult(
            final="test response",
            content="test response",
            response_time_secs=1.5
        )
        assert result.final == "test response"
        
        # Test ToolResult
        tool_result = ToolResult(
            tool="test_tool",
            success=True,
            public_text="success"
        )
        assert tool_result.success is True
        assert tool_result.tool == "test_tool"
        
        # Test PlannedToolCall
        call = PlannedToolCall(
            tool="test_tool",
            args={"key": "value"}
        )
        assert call.tool == "test_tool"
        assert call.options.passthrough is True  # Default
        
        # Test PlannerStep
        step = PlannerStep(calls=[], final_text="Done")
        assert step.final_text == "Done"
        assert step.calls == []
        
        print("[PASS] Pydantic models work correctly")
    except Exception as e:
        print(f"[FAIL] Error testing models: {e}")
        raise


def test_direct_response_tool():
    """Test DIRECT_RESPONSE internal tool."""
    try:
        from core.agents.passthrough_agent.agent import _direct_response_tool
        
        result = _direct_response_tool(response_text="Hello world")
        
        assert result.tool == "DIRECT_RESPONSE"
        assert result.success is True
        assert result.public_text == "Hello world"
        assert result.error is None
        
        print("[PASS] DIRECT_RESPONSE tool works correctly")
    except Exception as e:
        print(f"[FAIL] Error testing DIRECT_RESPONSE: {e}")
        raise


def test_initialize_runtime_includes_direct_response():
    """Test that runtime initialization includes DIRECT_RESPONSE tool."""
    try:
        import tempfile
        import core.agents.passthrough_agent.agent as agent_module
        
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_module.initialize_runtime(tool_root=tmpdir)
            
            # Should have DIRECT_RESPONSE even with no extensions
            assert "DIRECT_RESPONSE" in agent_module.TOOL_RUNNERS
            assert callable(agent_module.TOOL_RUNNERS["DIRECT_RESPONSE"])
        
        print("[PASS] Runtime initialization includes DIRECT_RESPONSE")
    except Exception as e:
        print(f"[FAIL] Error testing runtime initialization: {e}")
        raise


def test_extract_json_object():
    """Test JSON extraction from planner output."""
    try:
        from core.agents.passthrough_agent.agent import _extract_json_object
        
        # Test direct JSON
        result = _extract_json_object('{"calls": [], "final_text": "Done"}')
        assert result is not None
        assert "calls" in result
        assert "final_text" in result
        
        # Test JSON with surrounding text
        result = _extract_json_object('Here is the plan: {"calls": [], "final_text": "Done"} - end')
        assert result is not None
        assert "calls" in result
        
        # Test invalid JSON
        result = _extract_json_object("not json")
        assert result is None
        
        print("[PASS] JSON extraction works correctly")
    except Exception as e:
        print(f"[FAIL] Error testing JSON extraction: {e}")
        raise


def test_agent_signature():
    """Test agent function signatures."""
    try:
        from core.agents.passthrough_agent.agent import run_agent
        import inspect
        
        sig = inspect.signature(run_agent)
        params = list(sig.parameters.keys())
        
        assert 'user_prompt' in params
        assert 'chat_history' in params
        assert 'memory' in params
        assert 'tool_root' in params
        assert 'llm' in params
        
        print("[PASS] Agent signature is correct")
    except Exception as e:
        print(f"[FAIL] Error checking agent signature: {e}")
        raise


if __name__ == "__main__":
    print("Running passthrough agent tests...")
    
    test_agent_imports()
    test_agent_models()
    test_direct_response_tool()
    test_initialize_runtime_includes_direct_response()
    test_extract_json_object()
    test_agent_signature()
    
    print("\nAll tests passed!")

