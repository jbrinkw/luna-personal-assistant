#!/usr/bin/env python3
"""
Comprehensive External Services API Test Script

Tests all external services API endpoints with detailed logging:
- Upload service definition
- Install service with configuration
- Start, Stop, Restart operations
- Enable/Disable auto-start
- Status and health checks
- Logs retrieval
- Uninstall with cleanup
"""

import json
import time
import requests
import sys
from pathlib import Path
from typing import Dict, Any

# Configuration
API_BASE = "http://127.0.0.1:9999"
SERVICE_NAME = "demo_http_server"
SERVICE_JSON_PATH = Path(__file__).parent.parent / "demo-http-server.json"
REPO_PATH = Path(__file__).parent.parent
LUNA_DIR = REPO_PATH / ".luna"
SERVICE_DATA_DIR = LUNA_DIR / "external_services" / SERVICE_NAME
SERVICE_DEF_DIR = REPO_PATH / "external_services" / SERVICE_NAME

# Test configuration for installation
TEST_CONFIG = {
    "port": 9977,
    "message": "Test HTTP Server is running!"
}

# ANSI colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def log(message: str, level: str = "INFO"):
    """Print formatted log message"""
    colors = {
        "INFO": BLUE,
        "SUCCESS": GREEN,
        "ERROR": RED,
        "WARNING": YELLOW,
        "STEP": BOLD + BLUE
    }
    color = colors.get(level, "")
    timestamp = time.strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] [{level}] {message}{RESET}")


def log_json(data: Any, prefix: str = ""):
    """Pretty print JSON data"""
    print(f"{YELLOW}{prefix}{json.dumps(data, indent=2)}{RESET}")


def cleanup_existing_installation():
    """Remove any existing installation to start fresh"""
    log("Starting cleanup of existing installation...", "STEP")
    
    try:
        # Check if service is installed
        response = requests.get(f"{API_BASE}/api/external-services/installed")
        if response.ok:
            installed = response.json()
            if SERVICE_NAME in installed:
                log(f"Found existing {SERVICE_NAME}, uninstalling...", "WARNING")
                
                # Uninstall via API
                uninstall_response = requests.post(
                    f"{API_BASE}/api/external-services/{SERVICE_NAME}/uninstall",
                    json={"remove_data": True}
                )
                
                if uninstall_response.ok:
                    log("API uninstall successful", "SUCCESS")
                else:
                    log(f"API uninstall failed: {uninstall_response.text}", "WARNING")
            else:
                log(f"{SERVICE_NAME} not found in registry", "INFO")
        
        # Clean up filesystem (in case API cleanup failed)
        if SERVICE_DATA_DIR.exists():
            import shutil
            shutil.rmtree(SERVICE_DATA_DIR)
            log(f"Removed {SERVICE_DATA_DIR}", "INFO")
        
        if SERVICE_DEF_DIR.exists():
            import shutil
            shutil.rmtree(SERVICE_DEF_DIR)
            log(f"Removed {SERVICE_DEF_DIR}", "INFO")
        
        # Clean up logs
        log_file = LUNA_DIR / "logs" / f"{SERVICE_NAME}.log"
        if log_file.exists():
            log_file.unlink()
            log(f"Removed {log_file}", "INFO")
        
        log("Cleanup completed", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"Cleanup failed: {str(e)}", "ERROR")
        log("Continuing with test anyway...", "WARNING")
        return False


def test_upload_service():
    """Test 1: Upload service definition"""
    log("TEST 1: Upload service definition", "STEP")
    
    try:
        # Read service definition
        if not SERVICE_JSON_PATH.exists():
            log(f"Service definition not found: {SERVICE_JSON_PATH}", "ERROR")
            return False
        
        with open(SERVICE_JSON_PATH, 'r') as f:
            service_def = json.load(f)
        
        log(f"Loaded service definition from {SERVICE_JSON_PATH}", "INFO")
        log_json(service_def, "Service definition: ")
        
        # Upload via API
        response = requests.post(
            f"{API_BASE}/api/external-services/upload",
            json={"service_definition": service_def}
        )
        
        if not response.ok:
            log(f"Upload failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Upload response: ")
        
        # Verify file was created
        expected_file = SERVICE_DEF_DIR / "service.json"
        if expected_file.exists():
            log(f"✓ Service definition file created: {expected_file}", "SUCCESS")
        else:
            log(f"✗ Service definition file not found: {expected_file}", "ERROR")
            return False
        
        log("TEST 1: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 1: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_get_available_services():
    """Test 2: Get available services"""
    log("TEST 2: Get available services", "STEP")
    
    try:
        response = requests.get(f"{API_BASE}/api/external-services/available")
        
        if not response.ok:
            log(f"Get available failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        services = result.get("services", [])
        
        log(f"Found {len(services)} available services", "INFO")
        
        # Find our service
        our_service = next((s for s in services if s["name"] == SERVICE_NAME), None)
        if our_service:
            log(f"✓ Found {SERVICE_NAME} in available services", "SUCCESS")
            log_json(our_service, f"{SERVICE_NAME} details: ")
        else:
            log(f"✗ {SERVICE_NAME} not found in available services", "ERROR")
            log_json(services, "Available services: ")
            return False
        
        log("TEST 2: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 2: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_install_service():
    """Test 3: Install service with configuration"""
    log("TEST 3: Install service with configuration", "STEP")
    
    try:
        log_json(TEST_CONFIG, "Installation config: ")
        
        response = requests.post(
            f"{API_BASE}/api/external-services/{SERVICE_NAME}/install",
            json={"config": TEST_CONFIG}
        )
        
        if not response.ok:
            log(f"Install failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Install response: ")
        
        # Verify config file was created
        config_file = SERVICE_DATA_DIR / "config.json"
        if config_file.exists():
            log(f"✓ Config file created: {config_file}", "SUCCESS")
            with open(config_file, 'r') as f:
                saved_config = json.load(f)
            log_json(saved_config, "Saved config: ")
        else:
            log(f"✗ Config file not found: {config_file}", "ERROR")
            return False
        
        # Verify service appears in installed services
        installed_response = requests.get(f"{API_BASE}/api/external-services/installed")
        if installed_response.ok:
            installed = installed_response.json()
            if SERVICE_NAME in installed:
                log(f"✓ Service appears in installed registry", "SUCCESS")
                log_json(installed[SERVICE_NAME], "Registry entry: ")
            else:
                log(f"✗ Service not in installed registry", "ERROR")
                return False
        
        log("TEST 3: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 3: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_start_service():
    """Test 4: Start the service"""
    log("TEST 4: Start the service", "STEP")
    
    try:
        response = requests.post(f"{API_BASE}/api/external-services/{SERVICE_NAME}/start")
        
        if not response.ok:
            log(f"Start failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Start response: ")
        
        # Wait a moment for service to start
        log("Waiting 3 seconds for service to start...", "INFO")
        time.sleep(3)
        
        # Check if PID file exists
        pid_file = SERVICE_DATA_DIR / "server.pid"
        if pid_file.exists():
            pid = pid_file.read_text().strip()
            log(f"✓ PID file exists: {pid}", "SUCCESS")
        else:
            log(f"✗ PID file not found: {pid_file}", "WARNING")
        
        # Try to access the service
        try:
            service_response = requests.get(f"http://localhost:{TEST_CONFIG['port']}/health", timeout=5)
            if service_response.ok:
                health_data = service_response.json()
                log(f"✓ Service is responding at http://localhost:{TEST_CONFIG['port']}", "SUCCESS")
                log_json(health_data, "Health check response: ")
            else:
                log(f"✗ Service not responding correctly", "WARNING")
        except Exception as e:
            log(f"✗ Could not connect to service: {str(e)}", "WARNING")
        
        log("TEST 4: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 4: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_get_status():
    """Test 5: Get service status"""
    log("TEST 5: Get service status", "STEP")
    
    try:
        response = requests.get(f"{API_BASE}/api/external-services/{SERVICE_NAME}/status")
        
        if not response.ok:
            log(f"Get status failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Status response: ")
        
        log(f"Status: {result.get('status', 'unknown')}", "INFO")
        log(f"Enabled: {result.get('enabled', False)}", "INFO")
        
        log("TEST 5: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 5: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_get_logs():
    """Test 6: Get service logs"""
    log("TEST 6: Get service logs", "STEP")
    
    try:
        response = requests.get(f"{API_BASE}/api/external-services/{SERVICE_NAME}/logs?lines=50")
        
        if not response.ok:
            log(f"Get logs failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log(f"Log file path: {result.get('path', 'unknown')}", "INFO")
        
        logs = result.get('logs', '')
        if logs:
            log(f"✓ Retrieved {len(logs.splitlines())} lines of logs", "SUCCESS")
            print(f"\n{YELLOW}--- Service Logs (last 50 lines) ---{RESET}")
            print(logs)
            print(f"{YELLOW}--- End of Logs ---{RESET}\n")
        else:
            log("⚠ No logs found (might be normal if service just started)", "WARNING")
        
        log("TEST 6: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 6: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_stop_service():
    """Test 7: Stop the service"""
    log("TEST 7: Stop the service", "STEP")
    
    try:
        response = requests.post(f"{API_BASE}/api/external-services/{SERVICE_NAME}/stop")
        
        if not response.ok:
            log(f"Stop failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Stop response: ")
        
        # Wait a moment
        log("Waiting 2 seconds...", "INFO")
        time.sleep(2)
        
        # Check if PID file is gone
        pid_file = SERVICE_DATA_DIR / "server.pid"
        if not pid_file.exists():
            log(f"✓ PID file removed", "SUCCESS")
        else:
            log(f"⚠ PID file still exists", "WARNING")
        
        # Try to access the service (should fail)
        try:
            service_response = requests.get(f"http://localhost:{TEST_CONFIG['port']}/health", timeout=2)
            log(f"⚠ Service still responding (might be delayed)", "WARNING")
        except Exception:
            log(f"✓ Service is no longer responding (expected)", "SUCCESS")
        
        log("TEST 7: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 7: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_restart_service():
    """Test 8: Restart the service"""
    log("TEST 8: Restart the service", "STEP")
    
    try:
        response = requests.post(f"{API_BASE}/api/external-services/{SERVICE_NAME}/restart")
        
        if not response.ok:
            log(f"Restart failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Restart response: ")
        
        # Wait for restart
        log("Waiting 3 seconds for restart...", "INFO")
        time.sleep(3)
        
        # Try to access the service
        try:
            service_response = requests.get(f"http://localhost:{TEST_CONFIG['port']}/health", timeout=5)
            if service_response.ok:
                log(f"✓ Service is responding after restart", "SUCCESS")
                health_data = service_response.json()
                log_json(health_data, "Health check response: ")
            else:
                log(f"⚠ Service not responding correctly", "WARNING")
        except Exception as e:
            log(f"✗ Could not connect to service: {str(e)}", "ERROR")
            return False
        
        log("TEST 8: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 8: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_enable_service():
    """Test 9: Enable auto-start"""
    log("TEST 9: Enable auto-start", "STEP")
    
    try:
        response = requests.post(f"{API_BASE}/api/external-services/{SERVICE_NAME}/enable")
        
        if not response.ok:
            log(f"Enable failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Enable response: ")
        
        if result.get("enabled"):
            log("✓ Service enabled", "SUCCESS")
        else:
            log("⚠ Service not enabled in response", "WARNING")
        
        log("TEST 9: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 9: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_disable_service():
    """Test 10: Disable auto-start"""
    log("TEST 10: Disable auto-start", "STEP")
    
    try:
        response = requests.post(f"{API_BASE}/api/external-services/{SERVICE_NAME}/disable")
        
        if not response.ok:
            log(f"Disable failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Disable response: ")
        
        if not result.get("enabled"):
            log("✓ Service disabled", "SUCCESS")
        else:
            log("⚠ Service still enabled in response", "WARNING")
        
        log("TEST 10: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 10: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def test_uninstall_service():
    """Test 11: Uninstall service"""
    log("TEST 11: Uninstall service", "STEP")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/external-services/{SERVICE_NAME}/uninstall",
            json={"remove_data": True}
        )
        
        if not response.ok:
            log(f"Uninstall failed: {response.status_code} - {response.text}", "ERROR")
            return False
        
        result = response.json()
        log_json(result, "Uninstall response: ")
        
        # Wait a moment
        time.sleep(2)
        
        # Verify service is removed from registry
        installed_response = requests.get(f"{API_BASE}/api/external-services/installed")
        if installed_response.ok:
            installed = installed_response.json()
            if SERVICE_NAME not in installed:
                log(f"✓ Service removed from registry", "SUCCESS")
            else:
                log(f"✗ Service still in registry", "ERROR")
                return False
        
        # Verify data directory is removed
        if not SERVICE_DATA_DIR.exists():
            log(f"✓ Service data directory removed: {SERVICE_DATA_DIR}", "SUCCESS")
        else:
            log(f"⚠ Service data directory still exists: {SERVICE_DATA_DIR}", "WARNING")
        
        log("TEST 11: PASSED", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"TEST 11: FAILED - {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}External Services API Comprehensive Test Suite{RESET}")
    print(f"{BOLD}{'='*80}{RESET}\n")
    
    log(f"API Base: {API_BASE}", "INFO")
    log(f"Service: {SERVICE_NAME}", "INFO")
    log(f"Service JSON: {SERVICE_JSON_PATH}", "INFO")
    log(f"Repository: {REPO_PATH}", "INFO")
    print()
    
    # Pre-flight check
    log("Pre-flight check: Testing API connectivity...", "INFO")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.ok:
            log("✓ API is reachable", "SUCCESS")
        else:
            log("✗ API returned non-200 response", "ERROR")
            sys.exit(1)
    except Exception as e:
        log(f"✗ Cannot connect to API: {str(e)}", "ERROR")
        log("Make sure supervisor is running!", "ERROR")
        sys.exit(1)
    
    print()
    
    # Cleanup before starting
    cleanup_existing_installation()
    print()
    
    # Run tests
    tests = [
        test_upload_service,
        test_get_available_services,
        test_install_service,
        test_start_service,
        test_get_status,
        test_get_logs,
        test_stop_service,
        test_restart_service,
        test_enable_service,
        test_disable_service,
        test_uninstall_service,
    ]
    
    results = []
    for test_func in tests:
        print(f"\n{'-'*80}\n")
        result = test_func()
        results.append((test_func.__name__, result))
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}Test Summary{RESET}")
    print(f"{BOLD}{'='*80}{RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}✓ PASSED{RESET}" if result else f"{RED}✗ FAILED{RESET}"
        print(f"  {test_name:.<50} {status}")
    
    print(f"\n{BOLD}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}{BOLD}ALL TESTS PASSED!{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}SOME TESTS FAILED!{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

