#!/usr/bin/env python3
"""
Test Suite 1C.6: Full Update Cycle Integration Test
"""
import json
import os
import sys
import time
from pathlib import Path
from zipfile import ZipFile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.utils.http_client import get, post
from tests.utils.process_utils import start_bootstrap

REPO_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "-test"
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


def test_1c6_1_complete_flow():
    """Test 1C.6.1: Complete Update Flow"""
    print("Running Test 1C.6.1: Complete Update Flow...")
    
    result = {
        "test": "1C.6.1_complete_flow",
        "status": "pending",
        "system_shutdown": False,
        "updates_applied": False,
        "queue_deleted": False,
        "system_restarted": False,
        "health_check_pass": False
    }
    
    try:
        # Setup: Create test zip
        test_ext_source = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/test-extension-zip")
        zip_path = Path("/tmp/full_cycle_test.zip")
        
        with ZipFile(zip_path, 'w') as zipf:
            for file_path in test_ext_source.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(test_ext_source)
                    zipf.write(file_path, arcname)
        
        print(f"Created test zip: {zip_path}")
        
        # Create queue with multiple operations
        queue_data = {
            "operations": [
                {
                    "type": "install",
                    "source": "upload:full_cycle_test.zip",
                    "target": "cycle_test_ext"
                }
            ],
            "master_config": {
                "luna": {
                    "version": "10-19-25",
                    "timezone": "UTC",
                    "default_llm": "gpt-4"
                },
                "extensions": {
                    "cycle_test_ext": {
                        "enabled": True,
                        "source": "upload:full_cycle_test.zip",
                        "config": {}
                    }
                },
                "tool_configs": {},
                "port_assignments": {
                    "extensions": {},
                    "services": {}
                }
            }
        }
        
        # Save queue via API
        status_code, response = post(f"{BASE_URL}/queue/save", queue_data)
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Failed to save queue: {status_code}"
            return result
        
        print("Queue saved successfully")
        
        # Action: Trigger restart
        print("Triggering system restart...")
        status_code, response = post(f"{BASE_URL}/restart", {})
        
        if status_code != 200:
            result["status"] = "fail"
            result["error"] = f"Failed to trigger restart: {status_code}"
            return result
        
        print("Restart triggered")
        result["system_shutdown"] = True
        
        # Wait for shutdown
        print("Waiting for system to shutdown...")
        time.sleep(5)
        
        # Try to verify shutdown (health check should fail)
        try:
            status_code, _ = get(f"{BASE_URL}/health", timeout=2)
            if status_code == 200:
                print("WARNING: System still responding, may not have shut down")
        except:
            print("System appears to have shut down")
        
        # Wait for updates to apply and system to restart
        print("Waiting for updates to apply and system to restart...")
        time.sleep(15)
        
        # Poll for system restart
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                status_code, _ = get(f"{BASE_URL}/health", timeout=2)
                if status_code == 200:
                    print(f"System restarted after {attempt + 1} attempts")
                    result["system_restarted"] = True
                    result["health_check_pass"] = True
                    break
            except:
                pass
            
            if attempt < max_attempts - 1:
                time.sleep(2)
        
        if not result["system_restarted"]:
            result["status"] = "fail"
            result["error"] = "System did not restart within timeout"
            return result
        
        # Verify: Check if updates were applied
        ext_path = Path(REPO_PATH) / "extensions" / "cycle_test_ext"
        result["updates_applied"] = ext_path.exists()
        
        # Verify: Check if queue was deleted
        queue_path = Path(REPO_PATH) / "core" / "update_queue.json"
        result["queue_deleted"] = not queue_path.exists()
        
        if all([
            result["system_shutdown"],
            result["updates_applied"],
            result["queue_deleted"],
            result["system_restarted"],
            result["health_check_pass"]
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
    print("Phase 1C.6: Full Update Cycle Integration Test")
    print("=" * 60)
    print()
    
    # Start supervisor
    setup_test_environment()
    
    tests = [
        test_1c6_1_complete_flow
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



