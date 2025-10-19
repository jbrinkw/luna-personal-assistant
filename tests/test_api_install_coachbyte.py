#!/usr/bin/env python3
"""
Test direct GitHub install using Extension Manager API
Tests: github:jbrinkw/luna_ext_coachbyte:coachbyte
"""
import json
import sys
import subprocess
import time
import requests
from pathlib import Path

ACTIVE_DIR = "/root/luna/luna-personal-assistant"
TEST_DIR = "/root/luna/luna-personal-assistant-test"
API_BASE = "http://127.0.0.1:9999"


def reset_environment():
    """Reset test environment"""
    print("=" * 60)
    print("Resetting test environment...")
    print("=" * 60)
    
    # Stop any running Luna processes
    print("Stopping Luna processes...")
    subprocess.run(["pkill", "-9", "-f", "luna.sh"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "supervisor.py"], stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # Remove old test directory
    print(f"Removing old test environment: {TEST_DIR}")
    if Path(TEST_DIR).exists():
        import shutil
        shutil.rmtree(TEST_DIR)
    
    # Copy active to test
    print(f"Copying {ACTIVE_DIR} to {TEST_DIR}...")
    import shutil
    shutil.copytree(ACTIVE_DIR, TEST_DIR)
    
    # Ensure log directory exists
    log_dir = Path(TEST_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    print("Environment reset complete!")
    print()


def start_supervisor():
    """Start supervisor in background"""
    print("Starting supervisor...")
    
    # Start supervisor in background
    proc = subprocess.Popen(
        ["python3", f"{TEST_DIR}/supervisor/supervisor.py", TEST_DIR],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=TEST_DIR
    )
    
    # Wait for supervisor to be ready
    max_wait = 15
    for i in range(max_wait):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=1)
            if response.status_code == 200:
                print(f"✓ Supervisor started (PID: {proc.pid})")
                return proc
        except:
            pass
        time.sleep(1)
    
    print("✗ Supervisor failed to start")
    return None


def test_api_install_coachbyte():
    """Test installing coachbyte via API"""
    print("=" * 60)
    print("Test: Install CoachByte via Extension Manager API")
    print("=" * 60)
    print()
    
    result = {
        "test": "api_install_coachbyte",
        "status": "pending",
        "supervisor_started": False,
        "queue_saved": False,
        "restart_triggered": False,
        "extension_installed": False
    }
    
    supervisor_proc = None
    
    try:
        # Step 1: Start supervisor
        supervisor_proc = start_supervisor()
        if not supervisor_proc:
            raise Exception("Failed to start supervisor")
        result["supervisor_started"] = True
        
        # Step 2: Get current master config
        print("\n📋 Getting current master config...")
        response = requests.get(f"{API_BASE}/config/master")
        if response.status_code != 200:
            raise Exception(f"Failed to get master config: {response.status_code}")
        
        master_config = response.json()
        print(f"✓ Retrieved master config")
        
        # Step 3: Add coachbyte to extensions in master config
        if "extensions" not in master_config:
            master_config["extensions"] = {}
        
        master_config["extensions"]["coachbyte"] = {
            "enabled": True,
            "source": "github:jbrinkw/luna_ext_coachbyte:coachbyte",
            "config": {}
        }
        
        # Step 4: Create install queue
        print("\n📦 Creating installation queue...")
        queue_data = {
            "operations": [
                {
                    "type": "install",
                    "source": "github:jbrinkw/luna_ext_coachbyte:coachbyte",
                    "target": "coachbyte"
                }
            ],
            "master_config": master_config
        }
        
        # Step 5: Save queue via API
        response = requests.post(
            f"{API_BASE}/queue/save",
            json=queue_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to save queue: {response.status_code} - {response.text}")
        
        print(f"✓ Queue saved successfully")
        result["queue_saved"] = True
        
        # Verify queue was saved
        response = requests.get(f"{API_BASE}/queue/status")
        queue_status = response.json()
        print(f"  Queue status: {queue_status['operation_count']} operation(s)")
        
        # Step 6: Trigger restart via API
        print("\n🔄 Triggering system restart...")
        response = requests.post(f"{API_BASE}/restart")
        
        if response.status_code != 200:
            raise Exception(f"Failed to trigger restart: {response.status_code}")
        
        print(f"✓ Restart triggered")
        result["restart_triggered"] = True
        
        # Step 7: Wait for supervisor to shut down
        print("\n⏳ Waiting for supervisor to shut down...")
        time.sleep(3)
        
        # Step 8: Wait for apply_updates to complete
        print("⏳ Waiting for apply_updates to complete...")
        time.sleep(10)
        
        # Step 9: Verify extension was installed
        print("\n🔍 Verifying installation...")
        ext_path = Path(TEST_DIR) / "extensions" / "coachbyte"
        result["extension_installed"] = ext_path.exists()
        
        if result["extension_installed"]:
            print(f"✓ Extension installed at: {ext_path}")
            
            # Check for key files
            config_path = ext_path / "config.json"
            tools_dir = ext_path / "tools"
            ui_dir = ext_path / "ui"
            services_dir = ext_path / "services"
            
            files_found = []
            if config_path.exists():
                print(f"✓ Found config.json")
                files_found.append("config.json")
                with open(config_path) as f:
                    config = json.load(f)
                    print(f"  Extension: {config.get('name')}")
            if tools_dir.exists():
                print(f"✓ Found tools directory")
                files_found.append("tools/")
            if ui_dir.exists():
                print(f"✓ Found ui directory")
                files_found.append("ui/")
            if services_dir.exists():
                print(f"✓ Found services directory")
                files_found.append("services/")
            
            result["files_found"] = files_found
        else:
            print(f"✗ Extension not found at: {ext_path}")
        
        # Determine final status
        if all([
            result["supervisor_started"],
            result["queue_saved"],
            result["restart_triggered"],
            result["extension_installed"]
        ]):
            result["status"] = "pass"
            print("\n" + "=" * 60)
            print("TEST PASSED ✓")
            print("=" * 60)
        else:
            result["status"] = "fail"
            print("\n" + "=" * 60)
            print("TEST FAILED ✗")
            print("=" * 60)
    
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
        import traceback
        result["traceback"] = traceback.format_exc()
        print(f"\n✗ Exception occurred: {e}")
        print(traceback.format_exc())
    
    finally:
        # Clean up: kill supervisor if still running
        if supervisor_proc:
            try:
                print("\n🧹 Cleaning up...")
                supervisor_proc.terminate()
                supervisor_proc.wait(timeout=5)
            except:
                supervisor_proc.kill()
    
    return result


def main():
    """Run the test"""
    # Step 1: Reset environment
    reset_environment()
    
    # Step 2: Install coachbyte via API
    result = test_api_install_coachbyte()
    
    # Output JSON results
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()



