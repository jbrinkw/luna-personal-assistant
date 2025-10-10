"""Tests for LLM selector module."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.utils.llm_selector import get_default_model


def test_default_model():
    """Test that default model is gpt-4.1."""
    # Clear any existing env var
    original = os.environ.get('LLM_DEFAULT_MODEL')
    if 'LLM_DEFAULT_MODEL' in os.environ:
        del os.environ['LLM_DEFAULT_MODEL']
    
    try:
        default = get_default_model()
        assert default == 'gpt-4.1', f"Expected gpt-4.1, got {default}"
    finally:
        # Restore original
        if original:
            os.environ['LLM_DEFAULT_MODEL'] = original


def test_custom_model_from_env():
    """Test that custom model can be set via environment."""
    original = os.environ.get('LLM_DEFAULT_MODEL')
    
    try:
        os.environ['LLM_DEFAULT_MODEL'] = 'gpt-4-turbo'
        default = get_default_model()
        assert default == 'gpt-4-turbo'
    finally:
        if original:
            os.environ['LLM_DEFAULT_MODEL'] = original
        else:
            if 'LLM_DEFAULT_MODEL' in os.environ:
                del os.environ['LLM_DEFAULT_MODEL']


def test_get_chat_model_with_override():
    """Test getting chat model with explicit model override."""
    # This test just verifies the function exists and accepts parameters
    # Actual LLM instantiation requires API keys
    from core.utils.llm_selector import get_chat_model
    
    # Test that function is callable with expected parameters
    try:
        # We don't actually instantiate to avoid requiring API keys in tests
        assert callable(get_chat_model)
        print("[PASS] get_chat_model function is callable")
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        raise


if __name__ == "__main__":
    print("Running LLM selector tests...")
    
    test_default_model()
    print("[PASS] Default model test passed")
    
    test_custom_model_from_env()
    print("[PASS] Custom model from env test passed")
    
    test_get_chat_model_with_override()
    print("[PASS] get_chat_model callable test passed")
    
    print("\nAll tests passed!")

