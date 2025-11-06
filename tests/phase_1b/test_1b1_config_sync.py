#!/usr/bin/env python3
"""
Test Suite 1B.1: Config Sync Tests
"""
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.http_client import get, post
from tests.utils.process_utils import start_bootstrap
from tests.utils.file_utils import write_json, read_json, file_exists

REPO_PATH = "/root/luna/luna-hub-test"
SUPERVISOR_HOST = os.getenv('SUPERVISOR_HOST', '127.0.0.1')
BASE_URL = f"http://{SUPERVISOR_HOST}:9999"


def setup_test_environment():
    """Start supervisor for tests"""
    log_file = f"{REPO_PATH}/logs/test_bootstrap.log"
    start_bootstrap(REPO_PATH, log_file)
    time.sleep(8)  # Wait for supervisor to start
    
    # Verify health
    status_code, _ = get(f"{BASE_URL}/health")
    if status_code != 200:
        raise RuntimeError("Supervisor failed to start")


def test_1b1_1_basic_config_sync():
    """Test 1B.1.1: Basic Config Sync"""
    print("Running Test 1B.1.1: Basic Config Sync...")
    
    result = {
        "test": "1B.1.1_basic_config_sync",
        "status": "pending",
        "max_notes_updated": False,
        "theme_updated": False,
        "version_preserved": False,
        "auto_save_preserved": False,
        "enabled_added": False,
        "source_added": False,
        "final_config": {}
    }
    
    try:
        # Setup: Create test extension
        notes_path = Path(REPO_PATH) / "extensions" / "notes"
        notes_path.mkdir(parents=True, exist_ok=True)
        
        # Create extension config
        ext_config = {
            "version": "10-17-25",
            "max_notes": 100,
            "theme": "light",
            "auto_save": True,
            "required_secrets": ["OPENAI_API_KEY"]
        }
        write_json(notes_path / "config.json", ext_config)
        
        # Setup master config with different values
        master_config_path = Path(REPO_PATH) / "core" / "master_config.json"
        master_config = read_json(master_config_path)
        master_config["extensions"] = {
            "notes": {
                "enabled": True,
                "source": "github:user/notes",
                "config": {
                    "max_notes": 1000,
                    "theme": "dark"
                }
            }
        }
        write_json(master_config_path, master_config)
        
        # Action: Call config sync
        status_code, response = post(f"{BASE_URL}/config/sync", {})
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Config sync failed: {status_code}"
            return result
        
        # Verify: Read updated config
        updated_config = read_json(notes_path / "config.json")
        result["final_config"] = updated_config
        
        # Check updates
        result["max_notes_updated"] = updated_config.get("max_notes") == 1000
        result["theme_updated"] = updated_config.get("theme") == "dark"
        result["version_preserved"] = updated_config.get("version") == "10-17-25"
        result["auto_save_preserved"] = updated_config.get("auto_save") == True
        result["enabled_added"] = updated_config.get("enabled") == True
        result["source_added"] = updated_config.get("source") == "github:user/notes"
        
        # Overall status
        if all([
            result["max_notes_updated"],
            result["theme_updated"],
            result["version_preserved"],
            result["auto_save_preserved"],
            result["enabled_added"],
            result["source_added"]
        ]):
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def test_1b1_2_missing_version():
    """Test 1B.1.2: Missing Version Field Handling"""
    print("Running Test 1B.1.2: Missing Version Field Handling...")
    
    result = {
        "test": "1B.1.2_missing_version",
        "status": "pending",
        "version_added": False,
        "version_format_valid": False,
        "version_value": None
    }
    
    try:
        # Setup: Create extension without version
        todos_path = Path(REPO_PATH) / "extensions" / "todos"
        todos_path.mkdir(parents=True, exist_ok=True)
        
        ext_config = {
            "max_todos": 50,
            "auto_complete": True
        }
        write_json(todos_path / "config.json", ext_config)
        
        # Setup master config
        master_config_path = Path(REPO_PATH) / "core" / "master_config.json"
        master_config = read_json(master_config_path)
        if "extensions" not in master_config:
            master_config["extensions"] = {}
        master_config["extensions"]["todos"] = {
            "enabled": True,
            "source": "github:user/todos",
            "config": {}
        }
        write_json(master_config_path, master_config)
        
        # Action: Call config sync
        status_code, response = post(f"{BASE_URL}/config/sync", {})
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Config sync failed: {status_code}"
            return result
        
        # Verify: Check version was added
        updated_config = read_json(todos_path / "config.json")
        version = updated_config.get("version")
        result["version_value"] = version
        result["version_added"] = version is not None
        
        # Check format: MM-DD-YY
        import re
        if version:
            result["version_format_valid"] = bool(re.match(r'^\d{2}-\d{2}-\d{2}$', version))
        
        if result["version_added"] and result["version_format_valid"]:
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def test_1b1_3_tool_config_sync():
    """Test 1B.1.3: Tool Config Sync"""
    print("Running Test 1B.1.3: Tool Config Sync...")
    
    result = {
        "test": "1B.1.3_tool_config_sync",
        "status": "pending",
        "tool_config_updated": False,
        "enabled_in_mcp_correct": False,
        "passthrough_correct": False,
        "final_tool_config": {}
    }
    
    try:
        # Setup: Create extension with tool config
        notes_path = Path(REPO_PATH) / "extensions" / "notes"
        notes_path.mkdir(parents=True, exist_ok=True)
        (notes_path / "tools").mkdir(parents=True, exist_ok=True)
        
        # Create extension config
        ext_config = {"version": "10-17-25"}
        write_json(notes_path / "config.json", ext_config)
        
        # Create tool config
        tool_config = {
            "NOTES_CREATE_note": {
                "enabled_in_mcp": True,
                "passthrough": False
            }
        }
        write_json(notes_path / "tools" / "tool_config.json", tool_config)
        
        # Setup master config with different tool settings
        master_config_path = Path(REPO_PATH) / "core" / "master_config.json"
        master_config = read_json(master_config_path)
        master_config["extensions"] = {
            "notes": {
                "enabled": True,
                "source": "github:user/notes",
                "config": {}
            }
        }
        master_config["tool_configs"] = {
            "NOTES_CREATE_note": {
                "enabled_in_mcp": False,
                "passthrough": True
            }
        }
        write_json(master_config_path, master_config)
        
        # Action: Call config sync
        status_code, response = post(f"{BASE_URL}/config/sync", {})
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Config sync failed: {status_code}"
            return result
        
        # Verify: Check tool config updated
        updated_tool_config = read_json(notes_path / "tools" / "tool_config.json")
        result["final_tool_config"] = updated_tool_config.get("NOTES_CREATE_note", {})
        
        result["tool_config_updated"] = "NOTES_CREATE_note" in updated_tool_config
        result["enabled_in_mcp_correct"] = updated_tool_config.get("NOTES_CREATE_note", {}).get("enabled_in_mcp") == False
        result["passthrough_correct"] = updated_tool_config.get("NOTES_CREATE_note", {}).get("passthrough") == True
        
        if all([
            result["tool_config_updated"],
            result["enabled_in_mcp_correct"],
            result["passthrough_correct"]
        ]):
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def test_1b1_4_skip_missing():
    """Test 1B.1.4: Skip Missing Extensions"""
    print("Running Test 1B.1.4: Skip Missing Extensions...")
    
    result = {
        "test": "1B.1.4_skip_missing",
        "status": "pending",
        "sync_completed": True,
        "no_errors": True,
        "skipped": [],
        "synced": []
    }
    
    try:
        # Setup: Add missing extension to master config
        master_config_path = Path(REPO_PATH) / "core" / "master_config.json"
        master_config = read_json(master_config_path)
        
        # Add real extension
        notes_path = Path(REPO_PATH) / "extensions" / "notes"
        notes_path.mkdir(parents=True, exist_ok=True)
        write_json(notes_path / "config.json", {"version": "10-17-25"})
        
        master_config["extensions"] = {
            "notes": {
                "enabled": True,
                "source": "github:user/notes",
                "config": {}
            },
            "missing_extension": {
                "enabled": True,
                "source": "github:user/missing",
                "config": {}
            }
        }
        write_json(master_config_path, master_config)
        
        # Action: Call config sync
        status_code, response = post(f"{BASE_URL}/config/sync", {})
        
        if status_code != 200:
            result["sync_completed"] = False
            result["no_errors"] = False
            result["status"] = "fail"
            result["error"] = f"Config sync failed: {status_code}"
            return result
        
        # Verify: Check response
        result["skipped"] = response.get("skipped", [])
        result["synced"] = response.get("synced", [])
        
        if "missing_extension" in result["skipped"] and "notes" in result["synced"]:
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
        result["no_errors"] = False
    
    return result


def test_1b1_5_generic_matching():
    """Test 1B.1.5: Generic Key Matching"""
    print("Running Test 1B.1.5: Generic Key Matching...")
    
    result = {
        "test": "1B.1.5_generic_matching",
        "status": "pending",
        "preserved_a": False,
        "updated_b": False,
        "preserved_c": False,
        "did_not_add_d": True,
        "final_config": {}
    }
    
    try:
        # Setup: Create extension with specific keys
        test_path = Path(REPO_PATH) / "extensions" / "test_ext"
        test_path.mkdir(parents=True, exist_ok=True)
        
        ext_config = {
            "version": "10-17-25",
            "a": 1,
            "b": 2,
            "c": 3
        }
        write_json(test_path / "config.json", ext_config)
        
        # Setup master config with overlapping keys
        master_config_path = Path(REPO_PATH) / "core" / "master_config.json"
        master_config = read_json(master_config_path)
        master_config["extensions"] = {
            "test_ext": {
                "enabled": True,
                "source": "local",
                "config": {
                    "b": 20,
                    "d": 4
                }
            }
        }
        write_json(master_config_path, master_config)
        
        # Action: Call config sync
        status_code, response = post(f"{BASE_URL}/config/sync", {})
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Config sync failed: {status_code}"
            return result
        
        # Verify: Check key matching behavior
        updated_config = read_json(test_path / "config.json")
        result["final_config"] = updated_config
        
        result["preserved_a"] = updated_config.get("a") == 1
        result["updated_b"] = updated_config.get("b") == 20
        result["preserved_c"] = updated_config.get("c") == 3
        result["did_not_add_d"] = "d" not in updated_config  # Should NOT add new keys
        
        # Per the spec: only keys in extension get updated, don't add new keys from master
        if all([
            result["preserved_a"],
            result["updated_b"],
            result["preserved_c"],
            result["did_not_add_d"]
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
    print("Phase 1B.1: Config Sync Tests")
    print("=" * 60)
    print()
    
    # Start supervisor
    setup_test_environment()
    
    tests = [
        test_1b1_1_basic_config_sync,
        test_1b1_2_missing_version,
        test_1b1_3_tool_config_sync,
        test_1b1_4_skip_missing,
        test_1b1_5_generic_matching
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

