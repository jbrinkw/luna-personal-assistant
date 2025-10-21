#!/usr/bin/env python3
"""
Test Suite 1C.3: Delete and Update Operations Tests
"""
import json
import os
import sys
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

REPO_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "-test"


def test_1c3_1_delete_extension():
    """Test 1C.3.1: Delete Extension"""
    print("Running Test 1C.3.1: Delete Extension...")
    
    result = {
        "test": "1C.3.1_delete_extension",
        "status": "pending",
        "extension_deleted": False,
        "directory_removed": False
    }
    
    try:
        # Setup: Create extension to delete
        old_ext_path = Path(REPO_PATH) / "extensions" / "old_ext"
        old_ext_path.mkdir(parents=True, exist_ok=True)
        (old_ext_path / "config.json").write_text('{"version": "10-17-25"}')
        
        print(f"Created extension at: {old_ext_path}")
        
        # Create queue with delete operation
        queue_data = {
            "operations": [
                {
                    "type": "delete",
                    "target": "old_ext"
                }
            ],
            "master_config": {
                "luna": {"version": "10-19-25", "timezone": "UTC", "default_llm": "gpt-4"},
                "extensions": {},
                "tool_configs": {},
                "port_assignments": {"extensions": {}, "services": {}}
            }
        }
        
        # Save queue
        queue_path = Path(REPO_PATH) / "core" / "update_queue.json"
        with open(queue_path, 'w') as f:
            json.dump(queue_data, f, indent=2)
        
        print(f"Created queue at: {queue_path}")
        
        # Action: Run apply_updates
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
        
        # Verify: Check if extension was deleted
        result["extension_deleted"] = not old_ext_path.exists()
        result["directory_removed"] = not old_ext_path.exists()
        
        if result["extension_deleted"] and result["directory_removed"]:
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def test_1c3_3_update_upload():
    """Test 1C.3.3: Update Extension via Upload"""
    print("Running Test 1C.3.3: Update Extension via Upload...")
    
    result = {
        "test": "1C.3.3_update_upload",
        "status": "pending",
        "extension_updated": False,
        "old_removed": False,
        "new_installed": False
    }
    
    try:
        # Setup: Create old version of extension
        notes_path = Path(REPO_PATH) / "extensions" / "notes"
        notes_path.mkdir(parents=True, exist_ok=True)
        (notes_path / "config.json").write_text('{"version": "10-17-25"}')
        (notes_path / "old_file.txt").write_text("old content")
        
        print(f"Created old extension at: {notes_path}")
        
        # Create new version as zip
        test_ext_source = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/test-extension-zip")
        zip_path = Path("/tmp/notes_v2.zip")
        
        with ZipFile(zip_path, 'w') as zipf:
            for file_path in test_ext_source.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(test_ext_source)
                    zipf.write(file_path, arcname)
        
        print(f"Created new version zip: {zip_path}")
        
        # Create queue with update operation
        queue_data = {
            "operations": [
                {
                    "type": "update",
                    "source": "upload:notes_v2.zip",
                    "target": "notes"
                }
            ],
            "master_config": {
                "luna": {"version": "10-19-25", "timezone": "UTC", "default_llm": "gpt-4"},
                "extensions": {
                    "notes": {
                        "enabled": True,
                        "source": "upload:notes_v2.zip",
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
        
        # Action: Run apply_updates
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
        
        # Verify: Check if extension was updated
        result["extension_updated"] = notes_path.exists()
        result["old_removed"] = not (notes_path / "old_file.txt").exists()
        result["new_installed"] = (notes_path / "config.json").exists()
        
        if all([
            result["extension_updated"],
            result["old_removed"],
            result["new_installed"]
        ]):
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 1C.3: Delete and Update Operations Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_1c3_1_delete_extension,
        test_1c3_3_update_upload
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



