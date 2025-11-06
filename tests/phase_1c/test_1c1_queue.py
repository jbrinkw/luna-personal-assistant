#!/usr/bin/env python3
"""
Test Suite 1C.1: Update Queue Operations Tests
"""
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.http_client import get, post, delete
from tests.utils.process_utils import start_bootstrap
from tests.utils.file_utils import file_exists

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


def test_1c1_1_save_queue():
    """Test 1C.1.1: Save Queue"""
    print("Running Test 1C.1.1: Save Queue...")
    
    result = {
        "test": "1C.1.1_save_queue",
        "status": "pending",
        "file_created": False,
        "valid_json": False,
        "has_operations": False,
        "has_master_config": False
    }
    
    try:
        # Create queue data
        queue_data = {
            "operations": [
                {
                    "type": "install",
                    "source": "upload:test.zip",
                    "target": "test_ext"
                }
            ],
            "master_config": {
                "luna": {
                    "version": "10-19-25",
                    "timezone": "UTC",
                    "default_llm": "gpt-4"
                },
                "extensions": {},
                "tool_configs": {},
                "port_assignments": {
                    "extensions": {},
                    "services": {}
                }
            }
        }
        
        # Action: Save queue
        status_code, response = post(f"{BASE_URL}/queue/save", queue_data)
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Failed to save queue: {status_code}"
            return result
        
        # Verify: Check file created
        queue_path = Path(REPO_PATH) / "core" / "update_queue.json"
        result["file_created"] = queue_path.exists()
        
        if result["file_created"]:
            # Verify JSON structure
            with open(queue_path, 'r') as f:
                saved_queue = json.load(f)
            
            result["valid_json"] = isinstance(saved_queue, dict)
            result["has_operations"] = "operations" in saved_queue
            result["has_master_config"] = "master_config" in saved_queue
        
        if all([
            result["file_created"],
            result["valid_json"],
            result["has_operations"],
            result["has_master_config"]
        ]):
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def test_1c1_2_read_queue():
    """Test 1C.1.2: Read Queue"""
    print("Running Test 1C.1.2: Read Queue...")
    
    result = {
        "test": "1C.1.2_read_queue",
        "status": "pending",
        "queue_exists": False,
        "data_matches": False
    }
    
    try:
        # Setup: Create queue
        queue_data = {
            "operations": [
                {"type": "update", "target": "notes"}
            ],
            "master_config": {"luna": {"version": "10-19-25"}}
        }
        
        status_code, _ = post(f"{BASE_URL}/queue/save", queue_data)
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = "Failed to save queue for test setup"
            return result
        
        # Action: Read queue
        status_code, response = get(f"{BASE_URL}/queue/current")
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Failed to read queue: {status_code}"
            return result
        
        result["queue_exists"] = response.get("exists") != False
        
        # Verify data matches
        if "operations" in response and "master_config" in response:
            result["data_matches"] = (
                len(response["operations"]) == 1 and
                response["operations"][0]["type"] == "update"
            )
        
        if result["queue_exists"] and result["data_matches"]:
            result["status"] = "pass"
        else:
            result["status"] = "fail"
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    
    return result


def test_1c1_3_delete_queue():
    """Test 1C.1.3: Delete Queue"""
    print("Running Test 1C.1.3: Delete Queue...")
    
    result = {
        "test": "1C.1.3_delete_queue",
        "status": "pending",
        "file_deleted": False,
        "get_confirms_deleted": False
    }
    
    try:
        # Setup: Create queue
        queue_data = {
            "operations": [],
            "master_config": {}
        }
        
        status_code, _ = post(f"{BASE_URL}/queue/save", queue_data)
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = "Failed to save queue for test setup"
            return result
        
        # Action: Delete queue
        status_code, response = delete(f"{BASE_URL}/queue/current")
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Failed to delete queue: {status_code}"
            return result
        
        # Verify: Check file deleted
        queue_path = Path(REPO_PATH) / "core" / "update_queue.json"
        result["file_deleted"] = not queue_path.exists()
        
        # Verify: GET confirms deleted
        status_code, get_response = get(f"{BASE_URL}/queue/current")
        result["get_confirms_deleted"] = get_response.get("exists") == False
        
        if result["file_deleted"] and result["get_confirms_deleted"]:
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
    print("Phase 1C.1: Update Queue Operations Tests")
    print("=" * 60)
    print()
    
    # Start supervisor
    setup_test_environment()
    
    tests = [
        test_1c1_1_save_queue,
        test_1c1_2_read_queue,
        test_1c1_3_delete_queue
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



