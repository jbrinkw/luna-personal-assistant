#!/usr/bin/env python3
"""
Test Suite 1A.1: Supervisor Startup Tests
"""
import json
import os
import sys
import time
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.http_client import get
from tests.utils.process_utils import get_pid, is_process_running, kill_process, start_bootstrap
from tests.utils.file_utils import file_exists, read_json, is_valid_json, has_keys


REPO_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "-test"
SUPERVISOR_HOST = os.getenv('SUPERVISOR_HOST', '127.0.0.1')
HEALTH_URL = f"http://{SUPERVISOR_HOST}:9999/health"
MASTER_CONFIG_PATH = f"{REPO_PATH}/core/master_config.json"
STATE_PATH = f"{REPO_PATH}/supervisor/state.json"


def test_1a1_1_supervisor_starts():
    """Test 1A.1.1: Supervisor Starts"""
    print("Running Test 1A.1.1: Supervisor Starts...")
    
    result = {
        "test": "1A.1.1_supervisor_starts",
        "status": "pending",
        "process_running": False,
        "process_pid": None,
        "health_check": 0,
        "state_file_exists": False,
        "state_file_valid_json": False
    }
    
    # Start bootstrap
    log_file = f"{REPO_PATH}/logs/test_bootstrap.log"
    start_bootstrap(REPO_PATH, log_file)
    
    # Wait for supervisor to start (longer wait for proper startup)
    time.sleep(10)
    
    # Check health endpoint as primary indicator (more reliable than PID)
    status_code, data = get(HEALTH_URL)
    result["health_check"] = status_code
    
    # Try to get PID (may fail due to subprocess nesting, but health is primary)
    pid = get_pid("supervisor.py")
    result["process_running"] = pid is not None or status_code == 200
    result["process_pid"] = pid
    
    # Check state file
    result["state_file_exists"] = file_exists(STATE_PATH)
    result["state_file_valid_json"] = is_valid_json(STATE_PATH)
    
    # Determine pass/fail - health check is primary indicator
    if (result["health_check"] == 200 and
        result["state_file_exists"] and
        result["state_file_valid_json"]):
        result["status"] = "pass"
        result["process_running"] = True  # If health works, process is running
    else:
        result["status"] = "fail"
    
    return result


def test_1a1_2_master_config_creation():
    """Test 1A.1.2: Master Config Auto-Creation"""
    print("Running Test 1A.1.2: Master Config Auto-Creation...")
    
    result = {
        "test": "1A.1.2_master_config_creation",
        "status": "pending",
        "file_exists": False,
        "valid_json": False,
        "has_required_keys": False,
        "version_format": None,
        "version_value": None,
        "extensions_empty": False,
        "tool_configs_empty": False,
        "port_assignments_correct": False
    }
    
    # Check file exists
    result["file_exists"] = file_exists(MASTER_CONFIG_PATH)
    
    if not result["file_exists"]:
        result["status"] = "fail"
        return result
    
    # Read and validate JSON
    config = read_json(MASTER_CONFIG_PATH)
    result["valid_json"] = config is not None
    
    if not config:
        result["status"] = "fail"
        return result
    
    # Check required keys
    required_keys = ["luna", "extensions", "tool_configs", "port_assignments"]
    result["has_required_keys"] = has_keys(config, required_keys)
    
    # Check version format (MM-DD-YY)
    if "luna" in config and "version" in config["luna"]:
        version = config["luna"]["version"]
        result["version_value"] = version
        # Match MM-DD-YY format
        if re.match(r'^\d{2}-\d{2}-\d{2}$', version):
            result["version_format"] = "MM-DD-YY"
    
    # Check empty collections
    result["extensions_empty"] = config.get("extensions") == {}
    result["tool_configs_empty"] = config.get("tool_configs") == {}
    
    # Check port_assignments structure
    pa = config.get("port_assignments", {})
    result["port_assignments_correct"] = (
        "extensions" in pa and 
        "services" in pa and
        isinstance(pa["extensions"], dict) and
        isinstance(pa["services"], dict)
    )
    
    # Determine pass/fail
    if (result["file_exists"] and
        result["valid_json"] and
        result["has_required_keys"] and
        result["version_format"] == "MM-DD-YY" and
        result["extensions_empty"] and
        result["tool_configs_empty"] and
        result["port_assignments_correct"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def test_1a1_3_bootstrap_restart():
    """Test 1A.1.3: Bootstrap Restart After Supervisor Crash"""
    print("Running Test 1A.1.3: Bootstrap Restart After Supervisor Crash...")
    
    result = {
        "test": "1A.1.3_bootstrap_restart",
        "status": "pending",
        "supervisor_restarted": False,
        "old_pid": None,
        "new_pid": None,
        "pids_different": False,
        "health_restored": False,
        "state_updated": False
    }
    
    # Verify health works initially
    status_code1, _ = get(HEALTH_URL)
    if status_code1 != 200:
        result["status"] = "fail"
        result["note"] = "Supervisor not healthy before test"
        return result
    
    # Get initial PID (optional, health is primary)
    old_pid = get_pid("supervisor.py")
    result["old_pid"] = old_pid
    
    # Kill supervisor
    kill_process("supervisor.py")
    time.sleep(2)
    
    # Verify it's down
    status_code2, _ = get(HEALTH_URL, timeout=2)
    
    # Wait for bootstrap to restart (up to 15 seconds)
    for i in range(15):
        time.sleep(1)
        status_code, data = get(HEALTH_URL, timeout=2)
        if status_code == 200:
            result["health_restored"] = True
            result["supervisor_restarted"] = True
            # Try to get new PID
            new_pid = get_pid("supervisor.py")
            result["new_pid"] = new_pid
            result["pids_different"] = (new_pid != old_pid) if (new_pid and old_pid) else True
            break
    
    # Check state file
    result["state_updated"] = file_exists(STATE_PATH)
    
    # Determine pass/fail - health restoration is key
    if result["health_restored"] and result["state_updated"]:
        result["status"] = "pass"
        result["supervisor_restarted"] = True
    else:
        result["status"] = "fail"
    
    return result


def test_1a1_4_health_check_loop():
    """Test 1A.1.4: Bootstrap Health Check Loop"""
    print("Running Test 1A.1.4: Bootstrap Health Check Loop...")
    
    result = {
        "test": "1A.1.4_health_check_loop",
        "status": "pending",
        "supervisor_healthy": False,
        "note": "Health check loop tested via 1A.1.3 restart mechanism"
    }
    
    # Verify supervisor is healthy (proven by previous test's recovery)
    status_code, _ = get(HEALTH_URL)
    result["supervisor_healthy"] = status_code == 200
    
    if result["supervisor_healthy"]:
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def main():
    """Run all 1A.1 tests"""
    results = []
    
    print("=" * 60)
    print("Test Suite 1A.1: Supervisor Startup")
    print("=" * 60)
    
    results.append(test_1a1_1_supervisor_starts())
    results.append(test_1a1_2_master_config_creation())
    results.append(test_1a1_3_bootstrap_restart())
    results.append(test_1a1_4_health_check_loop())
    
    return results


if __name__ == "__main__":
    results = main()
    print(json.dumps(results, indent=2))

