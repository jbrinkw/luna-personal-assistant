"""Tests for Agent API server."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def test_agent_api_imports():
    """Test that agent API module can be imported."""
    try:
        from core.utils import agent_api
        assert hasattr(agent_api, 'app')
        assert hasattr(agent_api, '_discover_agents')
        assert hasattr(agent_api, '_init_agents')
        print("[PASS] Agent API module imports correctly")
    except Exception as e:
        print(f"[FAIL] Error importing agent API: {e}")
        raise


def test_discover_agents():
    """Test agent discovery."""
    try:
        from core.utils.agent_api import _discover_agents, AGENTS_ROOT
        
        # Should find simple_agent and passthrough_agent
        agents = _discover_agents()
        
        assert isinstance(agents, dict)
        # If agents exist, they should have run_agent method
        for agent_name, agent_mod in agents.items():
            assert hasattr(agent_mod, 'run_agent')
        
        print(f"[PASS] Agent discovery found {len(agents)} agent(s)")
    except Exception as e:
        print(f"[FAIL] Error discovering agents: {e}")
        raise


def test_split_history_and_prompt():
    """Test message splitting."""
    try:
        from core.utils.agent_api import _split_history_and_prompt, ChatMessage
        
        messages = [
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!"),
            ChatMessage(role="user", content="How are you?"),
        ]
        
        history, prompt = _split_history_and_prompt(messages)
        
        assert prompt == "How are you?"
        assert "Hello" in history
        assert "Hi there!" in history
        
        print("[PASS] Message splitting works correctly")
    except Exception as e:
        print(f"[FAIL] Error testing message splitting: {e}")
        raise


def test_extract_memory():
    """Test memory extraction from header."""
    try:
        from core.utils.agent_api import _extract_memory, ChatMessage
        
        messages = [ChatMessage(role="user", content="test")]
        
        # Test with header
        memory = _extract_memory(messages, "memory item 1\nmemory item 2")
        assert memory == "memory item 1\nmemory item 2"
        
        # Test without header
        memory = _extract_memory(messages, None)
        assert memory is None
        
        print("[PASS] Memory extraction works correctly")
    except Exception as e:
        print(f"[FAIL] Error testing memory extraction: {e}")
        raise


def test_chat_completion_payload():
    """Test OpenAI response payload generation."""
    try:
        from core.utils.agent_api import _make_chat_completion_payload
        
        payload = _make_chat_completion_payload("test_model", "test response")
        
        assert payload["object"] == "chat.completion"
        assert payload["model"] == "test_model"
        assert payload["choices"][0]["message"]["content"] == "test response"
        assert payload["choices"][0]["message"]["role"] == "assistant"
        assert "id" in payload
        assert "created" in payload
        
        print("[PASS] Chat completion payload generation works")
    except Exception as e:
        print(f"[FAIL] Error testing payload generation: {e}")
        raise


def test_fastapi_app_exists():
    """Test that FastAPI app is properly configured."""
    try:
        from core.utils.agent_api import app
        
        # Check routes exist
        routes = [route.path for route in app.routes]
        assert "/healthz" in routes
        assert "/v1/models" in routes
        assert "/v1/chat/completions" in routes
        
        print("[PASS] FastAPI app is properly configured")
    except Exception as e:
        print(f"[FAIL] Error checking FastAPI app: {e}")
        raise


if __name__ == "__main__":
    print("Running Agent API tests...")
    
    test_agent_api_imports()
    test_discover_agents()
    test_split_history_and_prompt()
    test_extract_memory()
    test_chat_completion_payload()
    test_fastapi_app_exists()
    
    print("\nAll tests passed!")

