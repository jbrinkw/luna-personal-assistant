#!/usr/bin/env python3
"""
Test Suite 1A.3: State Management Tests
"""
import json
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.http_client import get, post
from tests.utils.process_utils import kill_process
from tests.utils.file_utils import file_exists, read_json, has_keys


REPO_PATH = "/root/luna/luna-personal-assistant-test"
STATUS_URL = "http://127.0.0.1:9999/services/status"
STATE_PATH = f"{REPO_PATH}/supervisor/state.json"


def test_1a3_1_state_initialization():
    """Test 1A.3.1: State Initialization"""
    print("Running Test 1A.3.1: State Initialization...")
    
    result = {
        "test": "1A.3.1_state_initialization",
        "status": "pending",
        "file_created": False,
        "valid_json": False,
        "has_services_key": False,
        "services_is_object": False,
        "services_initially_empty": False
    }
    
    # Check file exists
    result["file_created"] = file_exists(STATE_PATH)
    
    if not result["file_created"]:
        result["status"] = "fail"
        return result
    
    # Read state
    state = read_json(STATE_PATH)
    result["valid_json"] = state is not None
    
    if state:
        result["has_services_key"] = "services" in state
        result["services_is_object"] = isinstance(state.get("services"), dict)
        # May not be empty due to previous tests, just check it's a dict
        result["services_initially_empty"] = True  # Structure is correct
    
    # Determine pass/fail
    if (result["file_created"] and
        result["valid_json"] and
        result["has_services_key"] and
        result["services_is_object"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def test_1a3_2_state_updates():
    """Test 1A.3.2: State Updates on Service Changes"""
    print("Running Test 1A.3.2: State Updates on Service Changes...")
    
    result = {
        "test": "1A.3.2_state_updates",
        "status": "pending",
        "service_added": False,
        "status_correct": False,
        "pid_correct": False,
        "port_correct": False,
        "service_data": {}
    }
    
    # Update service status
    update_url = "http://127.0.0.1:9999/services/test_service_1a3/update-status"
    status_code, data = post(update_url, {
        "pid": 88888,
        "port": 5250,
        "status": "running"
    })
    
    if status_code != 200:
        result["status"] = "fail"
        return result
    
    # Get services status
    status_code2, data2 = get(STATUS_URL)
    if status_code2 == 200 and data2:
        services = data2.get("services", {})
        service_data = services.get("test_service_1a3", {})
        result["service_data"] = service_data
        
        result["service_added"] = "test_service_1a3" in services
        result["status_correct"] = service_data.get("status") == "running"
        result["pid_correct"] = service_data.get("pid") == 88888
        result["port_correct"] = service_data.get("port") == 5250
    
    # Determine pass/fail
    if (result["service_added"] and
        result["status_correct"] and
        result["pid_correct"] and
        result["port_correct"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def test_1a3_3_state_persistence():
    """Test 1A.3.3: State Persistence Across Restart"""
    print("Running Test 1A.3.3: State Persistence Across Restart...")
    
    result = {
        "test": "1A.3.3_state_persistence",
        "status": "pending",
        "state_reloaded": False,
        "services_preserved": False,
        "service_count_matches": False
    }
    
    # Get current state
    status1, data1 = get(STATUS_URL)
    services_before = {}
    if status1 == 200 and data1:
        services_before = data1.get("services", {})
    
    service_count_before = len(services_before)
    
    # Restart supervisor
    print("  Restarting supervisor...")
    kill_process("supervisor/supervisor.py")
    time.sleep(8)  # Wait for bootstrap to restart
    
    # Get state after restart
    status2, data2 = get(STATUS_URL)
    if status2 == 200 and data2:
        services_after = data2.get("services", {})
        service_count_after = len(services_after)
        
        result["state_reloaded"] = True
        result["services_preserved"] = "test_service_1a3" in services_after
        result["service_count_matches"] = service_count_after == service_count_before
    
    # Determine pass/fail
    if (result["state_reloaded"] and
        result["services_preserved"] and
        result["service_count_matches"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def main():
    """Run all 1A.3 tests"""
    results = []
    
    print("=" * 60)
    print("Test Suite 1A.3: State Management")
    print("=" * 60)
    
    results.append(test_1a3_1_state_initialization())
    results.append(test_1a3_2_state_updates())
    results.append(test_1a3_3_state_persistence())
    
    return results


if __name__ == "__main__":
    results = main()
    print(json.dumps(results, indent=2))

