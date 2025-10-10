"""Tests for prompt runner module."""
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.utils.prompt_runner import run_prompts, _repo_root


def test_repo_root():
    """Test that _repo_root returns the correct path."""
    root = _repo_root()
    assert root.exists()
    assert root.is_dir()
    # Should have a CLAUDE.md file at root
    assert (root / 'CLAUDE.md').exists()


def test_run_prompts_validation():
    """Test input validation for run_prompts."""
    # Test with invalid input (not a list)
    try:
        run_prompts("not a list")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "must be a list" in str(e)
    
    # Test with invalid list items (not all strings)
    try:
        run_prompts([1, 2, 3])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "must be a list" in str(e)


def test_run_prompts_with_nonexistent_agent():
    """Test run_prompts with nonexistent agent path."""
    try:
        result = run_prompts(["test"], agent_path="nonexistent/agent.py")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_run_prompts_empty_list():
    """Test run_prompts with empty prompt list."""
    # Create a dummy agent that just exits successfully
    with tempfile.TemporaryDirectory() as tmpdir:
        agent_file = Path(tmpdir) / "dummy_agent.py"
        agent_file.write_text('''
import sys
sys.exit(0)
''')
        
        # Empty list should return success immediately
        result = run_prompts([], agent_path=str(agent_file))
        assert result == 0


if __name__ == "__main__":
    print("Running prompt runner tests...")
    
    test_repo_root()
    print("[PASS] Repo root test passed")
    
    test_run_prompts_validation()
    print("[PASS] Input validation test passed")
    
    test_run_prompts_with_nonexistent_agent()
    print("[PASS] Nonexistent agent test passed")
    
    test_run_prompts_empty_list()
    print("[PASS] Empty list test passed")
    
    print("\nAll tests passed!")

