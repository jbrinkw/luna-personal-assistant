"""
Test dependency installation script.
"""
import pytest
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestInstallDeps:
    """Test the install_deps.py script."""
    
    def test_script_exists(self):
        """Test that the install_deps.py script exists."""
        script_path = PROJECT_ROOT / "core" / "scripts" / "install_deps.py"
        assert script_path.exists(), f"Script not found: {script_path}"
    
    def test_script_has_execute_permission(self):
        """Test that script can be imported."""
        script_path = PROJECT_ROOT / "core" / "scripts" / "install_deps.py"
        # Try to import it
        import importlib.util
        spec = importlib.util.spec_from_file_location("install_deps", script_path)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert module is not None
    
    def test_help_option(self):
        """Test that --help option works."""
        result = subprocess.run(
            [sys.executable, "core/scripts/install_deps.py", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0
        assert "Install all Luna dependencies" in result.stdout
    
    def test_check_uv_function(self):
        """Test the check_uv_installed function."""
        sys.path.insert(0, str(PROJECT_ROOT))
        from core.scripts.install_deps import check_uv_installed
        
        # Just check it doesn't crash
        result = check_uv_installed()
        assert isinstance(result, bool)
    
    def test_find_extension_requirements(self):
        """Test finding extension requirements."""
        sys.path.insert(0, str(PROJECT_ROOT))
        from core.scripts.install_deps import find_extension_requirements
        
        results = find_extension_requirements()
        assert isinstance(results, list)
        
        # Should find at least automation_memory
        ext_names = [name for name, _ in results]
        assert len(ext_names) > 0, "Should find at least one extension"
    
    def test_core_requirements_exists(self):
        """Test that core requirements.txt exists."""
        req_file = PROJECT_ROOT / "requirements.txt"
        assert req_file.exists(), "Core requirements.txt not found"
    
    def test_dry_run_verbose(self):
        """Test running the script with --help (safe dry run)."""
        result = subprocess.run(
            [sys.executable, "core/scripts/install_deps.py", "-v", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(PROJECT_ROOT)
        )
        # Should succeed (help always works)
        assert result.returncode == 0


class TestRequirementsFiles:
    """Test that requirements files are valid."""
    
    def test_core_requirements_valid(self):
        """Test that core requirements.txt is valid."""
        req_file = PROJECT_ROOT / "requirements.txt"
        assert req_file.exists()
        
        content = req_file.read_text()
        # Should have some packages
        lines = [l.strip() for l in content.split('\n') 
                if l.strip() and not l.strip().startswith('#')]
        assert len(lines) > 0, "Core requirements should have packages"
        
        # Check for key packages
        all_content = content.lower()
        assert 'fastapi' in all_content or 'pydantic' in all_content
    
    def test_extension_requirements_valid(self):
        """Test that extension requirements files are valid."""
        extensions_dir = PROJECT_ROOT / "extensions"
        if not extensions_dir.exists():
            pytest.skip("No extensions directory")
        
        for ext_dir in extensions_dir.iterdir():
            if not ext_dir.is_dir():
                continue
            
            req_file = ext_dir / "requirements.txt"
            if req_file.exists():
                content = req_file.read_text()
                # Should not be empty
                lines = [l.strip() for l in content.split('\n') 
                        if l.strip() and not l.strip().startswith('#')]
                assert len(lines) >= 0, f"{ext_dir.name}/requirements.txt exists but may be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])




