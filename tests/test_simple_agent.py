"""Tests for simple agent module."""
import os
import sys
import tempfile
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_agent_imports():
    """Test that agent module can be imported."""
    try:
        from core.agents.simple_agent import agent
        assert hasattr(agent, 'run_agent')
        assert hasattr(agent, 'run_agent_stream')
        assert hasattr(agent, 'initialize_runtime')
        print("[PASS] Agent module imports correctly")
    except Exception as e:
        print(f"[FAIL] Error importing agent: {e}")
        raise


def test_agent_models():
    """Test that Pydantic models are properly defined."""
    try:
        from core.agents.simple_agent.agent import AgentResult, ToolTrace, Timing
        
        # Test AgentResult model
        result = AgentResult(
            final="test response",
            content="test response",
            response_time_secs=1.5
        )
        assert result.final == "test response"
        assert result.response_time_secs == 1.5
        assert result.traces == []
        
        # Test ToolTrace model
        trace = ToolTrace(
            tool="test_tool",
            args={"key": "value"},
            output="success",
            duration_secs=0.5
        )
        assert trace.tool == "test_tool"
        assert trace.duration_secs == 0.5
        
        # Test Timing model
        timing = Timing(name="test_operation", seconds=2.0)
        assert timing.name == "test_operation"
        assert timing.seconds == 2.0
        
        print("[PASS] Pydantic models work correctly")
    except Exception as e:
        print(f"[FAIL] Error testing models: {e}")
        raise


def test_initialize_runtime_empty():
    """Test runtime initialization with no extensions."""
    try:
        from core.agents.simple_agent.agent import initialize_runtime, PRELOADED_TOOLS
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize with empty directory
            initialize_runtime(tool_root=tmpdir)
            # PRELOADED_TOOLS should be empty list
            assert isinstance(PRELOADED_TOOLS, list)
            
        print("[PASS] Runtime initialization with empty directory works")
    except Exception as e:
        print(f"[FAIL] Error initializing runtime: {e}")
        raise


def test_wrap_callable_as_tool():
    """Test wrapping a Python function as a LangChain tool."""
    try:
        from core.agents.simple_agent.agent import _wrap_callable_as_tool
        
        def test_tool(query: str, count: int = 1) -> str:
            """Test tool for testing.
            Example Prompt: run test with query
            Example Response: {"result": "ok"}
            Example Args: {"query": "test", "count": 1}
            """
            return f"Result: {query} x {count}"
        
        wrapped = _wrap_callable_as_tool(test_tool, "test_ext")
        
        assert wrapped.name == "test_tool"
        assert callable(wrapped.func)
        
        print("[PASS] Function wrapping works correctly")
    except Exception as e:
        print(f"[FAIL] Error wrapping function: {e}")
        raise


def test_agent_result_with_mock_extension():
    """Test agent with a mock extension (integration test - requires LLM)."""
    # This test would require API keys and a real LLM, so we skip actual execution
    # Just verify the agent structure is correct
    try:
        from core.agents.simple_agent.agent import run_agent
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
    print("Running simple agent tests...")
    
    test_agent_imports()
    test_agent_models()
    test_initialize_runtime_empty()
    test_wrap_callable_as_tool()
    test_agent_result_with_mock_extension()
    
    print("\nAll tests passed!")

