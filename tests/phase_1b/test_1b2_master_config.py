#!/usr/bin/env python3
"""
Test Suite 1B.2: Master Config Operations Tests
"""
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.http_client import get, put, patch
from tests.utils.process_utils import start_bootstrap
from tests.utils.file_utils import read_json, write_json

REPO_PATH = "/root/luna/luna-hub-test"
SUPERVISOR_HOST = os.getenv('SUPERVISOR_HOST', '127.0.0.1')
BASE_URL = f"http://{SUPERVISOR_HOST}:9999"


def setup_test_environment():
    """Start supervisor for tests"""
    log_file = f"{REPO_PATH}/logs/test_bootstrap.log"
    start_bootstrap(REPO_PATH, log_file)
    time.sleep(8)
    
    # Verify health
    status_code, _ = get(f"{BASE_URL}/health")
    if status_code != 200:
        raise RuntimeError("Supervisor failed to start")


def test_1b2_1_read_master():
    """Test 1B.2.1: Read Master Config"""
    print("Running Test 1B.2.1: Read Master Config...")
    
    result = {
        "test": "1B.2.1_read_master",
        "status": "pending",
        "received_data": False,
        "has_all_sections": False,
        "valid_json": False
    }
    
    try:
        # Action: Get master config
        status_code, response = get(f"{BASE_URL}/config/master")
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Failed to read master config: {status_code}"
            return result
        
        result["received_data"] = response is not None
        result["valid_json"] = isinstance(response, dict)
        
        # Check for required sections
        required_sections = ["luna", "extensions", "tool_configs", "port_assignments"]
        result["has_all_sections"] = all(section in response for section in required_sections)
        
        if all([
            result["received_data"],
            result["has_all_sections"],
            result["valid_json"]
        ]):
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def test_1b2_2_update_extension():
    """Test 1B.2.2: Update Extension in Master Config"""
    print("Running Test 1B.2.2: Update Extension in Master Config...")
    
    result = {
        "test": "1B.2.2_update_extension",
        "status": "pending",
        "master_config_updated": False,
        "enabled_correct": False,
        "config_correct": False,
        "persisted_to_disk": False
    }
    
    try:
        # Setup: Ensure notes extension exists in master
        master_config_path = Path(REPO_PATH) / "core" / "master_config.json"
        master_config = read_json(master_config_path)
        if "extensions" not in master_config:
            master_config["extensions"] = {}
        master_config["extensions"]["notes"] = {
            "enabled": True,
            "source": "github:user/notes",
            "config": {"max_notes": 100}
        }
        write_json(master_config_path, master_config)
        
        # Action: Update extension via API
        update_data = {
            "enabled": False,
            "config": {"max_notes": 2000}
        }
        status_code, response = patch(f"{BASE_URL}/config/master/extensions/notes", update_data)
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Failed to update extension: {status_code}"
            return result
        
        result["master_config_updated"] = response.get("updated") == True
        
        # Verify: Read master config from disk
        updated_master = read_json(master_config_path)
        notes_config = updated_master.get("extensions", {}).get("notes", {})
        
        result["enabled_correct"] = notes_config.get("enabled") == False
        result["config_correct"] = notes_config.get("config", {}).get("max_notes") == 2000
        result["persisted_to_disk"] = True
        
        if all([
            result["master_config_updated"],
            result["enabled_correct"],
            result["config_correct"],
            result["persisted_to_disk"]
        ]):
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def test_1b2_3_update_tool():
    """Test 1B.2.3: Update Tool Config in Master"""
    print("Running Test 1B.2.3: Update Tool Config in Master...")
    
    result = {
        "test": "1B.2.3_update_tool",
        "status": "pending",
        "tool_config_updated": False,
        "values_correct": False,
        "persisted": False
    }
    
    try:
        # Action: Update tool config
        tool_config = {
            "enabled_in_mcp": True,
            "passthrough": True
        }
        status_code, response = patch(f"{BASE_URL}/config/master/tool/NOTES_CREATE_note", tool_config)
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Failed to update tool config: {status_code}"
            return result
        
        result["tool_config_updated"] = response.get("updated") == True
        
        # Verify: Read master config from disk
        master_config_path = Path(REPO_PATH) / "core" / "master_config.json"
        updated_master = read_json(master_config_path)
        
        tool = updated_master.get("tool_configs", {}).get("NOTES_CREATE_note", {})
        result["values_correct"] = (
            tool.get("enabled_in_mcp") == True and
            tool.get("passthrough") == True
        )
        result["persisted"] = True
        
        if all([
            result["tool_config_updated"],
            result["values_correct"],
            result["persisted"]
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
    print("Phase 1B.2: Master Config Operations Tests")
    print("=" * 60)
    print()
    
    # Start supervisor
    setup_test_environment()
    
    tests = [
        test_1b2_1_read_master,
        test_1b2_2_update_extension,
        test_1b2_3_update_tool
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



