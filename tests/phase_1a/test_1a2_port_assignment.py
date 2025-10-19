#!/usr/bin/env python3
"""
Test Suite 1A.2: Port Assignment Tests
"""
import json
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.http_client import get, post
from tests.utils.process_utils import kill_process, start_bootstrap
from tests.utils.file_utils import read_json


REPO_PATH = "/root/luna/luna-personal-assistant-test"
PORTS_URL = "http://127.0.0.1:9999/ports"
ASSIGN_URL = "http://127.0.0.1:9999/ports/assign"
MASTER_CONFIG_PATH = f"{REPO_PATH}/core/master_config.json"


def test_1a2_1_extension_port_assignment():
    """Test 1A.2.1: Extension Port Assignment"""
    print("Running Test 1A.2.1: Extension Port Assignment...")
    
    result = {
        "test": "1A.2.1_extension_port_assignment",
        "status": "pending",
        "notes_port": None,
        "todos_port": None,
        "ports_sequential": False,
        "saved_to_master_config": False,
        "master_config_extensions": {}
    }
    
    # Assign port to notes
    status1, data1 = post(ASSIGN_URL, {"type": "extension", "name": "notes"})
    if status1 == 200 and data1:
        result["notes_port"] = data1.get("port")
    
    # Assign port to todos
    status2, data2 = post(ASSIGN_URL, {"type": "extension", "name": "todos"})
    if status2 == 200 and data2:
        result["todos_port"] = data2.get("port")
    
    # Check sequential
    if result["notes_port"] == 5200 and result["todos_port"] == 5201:
        result["ports_sequential"] = True
    
    # Add delay for file sync
    time.sleep(1)
    
    # Check master_config
    config = read_json(MASTER_CONFIG_PATH)
    if config:
        extensions = config.get("port_assignments", {}).get("extensions", {})
        result["master_config_extensions"] = extensions
        result["saved_to_master_config"] = (
            extensions.get("notes") == 5200 and
            extensions.get("todos") == 5201
        )
    
    # Determine pass/fail
    if (result["notes_port"] == 5200 and
        result["todos_port"] == 5201 and
        result["saved_to_master_config"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def test_1a2_2_port_persistence():
    """Test 1A.2.2: Port Reuse After Restart"""
    print("Running Test 1A.2.2: Port Reuse After Restart...")
    
    result = {
        "test": "1A.2.2_port_persistence",
        "status": "pending",
        "notes_port_stable": False,
        "todos_port_stable": False,
        "notes_port": None,
        "todos_port": None
    }
    
    # Get current ports
    status1, data1 = get(PORTS_URL)
    ports_before = {}
    if status1 == 200 and data1:
        ports_before = data1.get("extensions", {})
    
    # Restart supervisor
    print("  Restarting supervisor...")
    kill_process("supervisor/supervisor.py")
    time.sleep(8)  # Wait for bootstrap to restart
    
    # Get ports after restart
    status2, data2 = get(PORTS_URL)
    if status2 == 200 and data2:
        ports_after = data2.get("extensions", {})
        result["notes_port"] = ports_after.get("notes")
        result["todos_port"] = ports_after.get("todos")
        
        # Check if ports are stable
        result["notes_port_stable"] = (
            ports_after.get("notes") == ports_before.get("notes") and
            ports_after.get("notes") == 5200
        )
        result["todos_port_stable"] = (
            ports_after.get("todos") == ports_before.get("todos") and
            ports_after.get("todos") == 5201
        )
    
    # Determine pass/fail
    if result["notes_port_stable"] and result["todos_port_stable"]:
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def test_1a2_3_service_port_assignment():
    """Test 1A.2.3: Service Port Assignment with Key"""
    print("Running Test 1A.2.3: Service Port Assignment with Key...")
    
    result = {
        "test": "1A.2.3_service_port_assignment",
        "status": "pending",
        "port": None,
        "port_in_range": False,
        "key_format_correct": False,
        "key": "github_sync.webhook_receiver",
        "saved_to_master_config": False
    }
    
    # Assign service port
    status, data = post(ASSIGN_URL, {
        "type": "service",
        "name": "github_sync.webhook_receiver",
        "requires_port": True
    })
    
    if status == 200 and data:
        result["port"] = data.get("port")
        result["port_in_range"] = result["port"] >= 5300
        result["key_format_correct"] = "." in result["key"]
    
    # Add delay for file sync
    time.sleep(1)
    
    # Check master_config
    config = read_json(MASTER_CONFIG_PATH)
    if config:
        services = config.get("port_assignments", {}).get("services", {})
        result["saved_to_master_config"] = (
            services.get("github_sync.webhook_receiver") == result["port"]
        )
    
    # Determine pass/fail
    if (result["port_in_range"] and
        result["key_format_correct"] and
        result["saved_to_master_config"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def test_1a2_4_service_no_port():
    """Test 1A.2.4: No Port for Service Without requires_port"""
    print("Running Test 1A.2.4: No Port for Service Without requires_port...")
    
    result = {
        "test": "1A.2.4_service_no_port",
        "status": "pending",
        "port": "not_null",
        "saved_as_null": False,
        "key_exists_in_config": False,
        "key": "email.worker"
    }
    
    # Assign service without port
    status, data = post(ASSIGN_URL, {
        "type": "service",
        "name": "email.worker",
        "requires_port": False
    })
    
    if status == 200 and data:
        result["port"] = data.get("port")
    
    # Check master_config
    config = read_json(MASTER_CONFIG_PATH)
    if config:
        services = config.get("port_assignments", {}).get("services", {})
        result["key_exists_in_config"] = "email.worker" in services
        result["saved_as_null"] = services.get("email.worker") is None
    
    # Determine pass/fail
    if (result["port"] is None and
        result["saved_as_null"] and
        result["key_exists_in_config"]):
        result["status"] = "pass"
    else:
        result["status"] = "fail"
    
    return result


def main():
    """Run all 1A.2 tests"""
    results = []
    
    print("=" * 60)
    print("Test Suite 1A.2: Port Assignment")
    print("=" * 60)
    
    results.append(test_1a2_1_extension_port_assignment())
    results.append(test_1a2_2_port_persistence())
    results.append(test_1a2_3_service_port_assignment())
    results.append(test_1a2_4_service_no_port())
    
    return results


if __name__ == "__main__":
    results = main()
    print(json.dumps(results, indent=2))

