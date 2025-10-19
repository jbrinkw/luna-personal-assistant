#!/usr/bin/env python3
"""
Test Suite 1C.2: Install Operations Tests
"""
import json
import sys
import time
import shutil
from pathlib import Path
from zipfile import ZipFile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.http_client import post
from tests.utils.file_utils import file_exists

REPO_PATH = "/root/luna/luna-personal-assistant-test"
BASE_URL = "http://127.0.0.1:9999"


def create_test_zip():
    """Create a test extension zip file"""
    test_ext_source = Path("/root/luna/test-extension-zip")
    zip_path = Path("/tmp/test_extension_install.zip")
    
    # Create zip file
    with ZipFile(zip_path, 'w') as zipf:
        for file_path in test_ext_source.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(test_ext_source)
                zipf.write(file_path, arcname)
    
    return zip_path


def test_1c2_3_install_upload():
    """Test 1C.2.3: Install from Upload"""
    print("Running Test 1C.2.3: Install from Upload...")
    
    result = {
        "test": "1C.2.3_install_upload",
        "status": "pending",
        "extension_installed": False,
        "files_extracted": False,
        "structure_correct": False
    }
    
    try:
        # Setup: Create test zip
        zip_path = create_test_zip()
        print(f"Created test zip: {zip_path}")
        
        # Create queue with install operation
        queue_data = {
            "operations": [
                {
                    "type": "install",
                    "source": "upload:test_extension_install.zip",
                    "target": "test_extension"
                }
            ],
            "master_config": {
                "luna": {"version": "10-19-25", "timezone": "UTC", "default_llm": "gpt-4"},
                "extensions": {
                    "test_extension": {
                        "enabled": True,
                        "source": "upload:test_extension_install.zip",
                        "config": {}
                    }
                },
                "tool_configs": {},
                "port_assignments": {"extensions": {}, "services": {}}
            }
        }
        
        # Save queue
        queue_path = Path(REPO_PATH) / "core" / "update_queue.json"
        with open(queue_path, 'w') as f:
            json.dump(queue_data, f, indent=2)
        
        print(f"Created queue at: {queue_path}")
        
        # Action: Run apply_updates manually
        import subprocess
        apply_updates_script = Path(REPO_PATH) / "core" / "scripts" / "apply_updates.py"
        
        print("Running apply_updates.py...")
        result_proc = subprocess.run(
            ["python3", str(apply_updates_script), REPO_PATH],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print("apply_updates output:")
        print(result_proc.stdout)
        if result_proc.stderr:
            print("Errors:")
            print(result_proc.stderr)
        
        # Note: apply_updates will try to restart luna.sh at the end
        # This is expected to fail in test environment, ignore exit code
        
        # Verify: Check if extension was installed
        ext_path = Path(REPO_PATH) / "extensions" / "test_extension"
        result["extension_installed"] = ext_path.exists()
        
        if result["extension_installed"]:
            # Check for key files
            config_exists = (ext_path / "config.json").exists()
            tools_exists = (ext_path / "tools" / "test_tools.py").exists()
            service_exists = (ext_path / "services" / "test_service" / "server.py").exists()
            
            result["files_extracted"] = all([config_exists, tools_exists, service_exists])
            result["structure_correct"] = result["files_extracted"]
        
        if all([
            result["extension_installed"],
            result["files_extracted"],
            result["structure_correct"]
        ]):
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
        import traceback
        result["traceback"] = traceback.format_exc()
    
    return result


def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 1C.2: Install Operations Tests")
    print("=" * 60)
    print()
    
    # Note: No supervisor needed for these tests
    # We run apply_updates directly
    
    tests = [
        test_1c2_3_install_upload
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
            print(f"  {result['test']}: {result['status']}")
        except Exception as e:
            print(f"  Test failed with exception: {e}")
            results.append({
                "test": test_func.__name__,
                "status": "error",
                "error": str(e)
            })
        print()
    
    # Output JSON results
    print(json.dumps(results, indent=2))
    
    return results


if __name__ == "__main__":
    main()



