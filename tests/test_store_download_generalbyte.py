#!/usr/bin/env python3
"""
Simple test to reset environment and download generalbyte extension from store
"""
import json
import os
import sys
import subprocess
import shutil
from pathlib import Path

ACTIVE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = "/root/luna/luna-personal-assistant-test"

def reset_environment():
    """Reset test environment by copying active dir to test dir"""
    print("=" * 60)
    print("Resetting test environment...")
    print("=" * 60)
    
    # Stop any running Luna processes
    print("Stopping Luna processes...")
    subprocess.run(["pkill", "-9", "-f", "luna.sh"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "supervisor.py"], stderr=subprocess.DEVNULL)
    
    import time
    time.sleep(2)
    
    # Remove old test directory
    print(f"Removing old test environment: {TEST_DIR}")
    if Path(TEST_DIR).exists():
        shutil.rmtree(TEST_DIR)
    
    # Copy active to test
    print(f"Copying {ACTIVE_DIR} to {TEST_DIR}...")
    shutil.copytree(ACTIVE_DIR, TEST_DIR)
    
    # Ensure log directory exists
    log_dir = Path(TEST_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    print("Environment reset complete!")
    print()


def test_download_generalbyte():
    """Download generalbyte extension from store"""
    print("=" * 60)
    print("Test: Download GeneralByte Extension from Store")
    print("=" * 60)
    print()
    
    result = {
        "test": "download_generalbyte_from_store",
        "status": "pending",
        "queue_created": False,
        "apply_updates_ran": False,
        "extension_installed": False
    }
    
    try:
        # Create queue with install operation for generalbyte from store
        # Using correct repository: jbrinkw/luna-ext-store
        queue_data = {
            "operations": [
                {
                    "type": "install",
                    "source": "github:jbrinkw/luna-ext-store:embedded/generalbyte",
                    "target": "generalbyte"
                }
            ],
            "master_config": {
                "luna": {
                    "version": "10-19-25",
                    "timezone": "UTC",
                    "default_llm": "gpt-4"
                },
                "extensions": {
                    "generalbyte": {
                        "enabled": True,
                        "source": "github:jbrinkw/luna-ext-store:embedded/generalbyte",
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
        
        # Save queue to test directory
        queue_path = Path(TEST_DIR) / "core" / "update_queue.json"
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(queue_path, 'w') as f:
            json.dump(queue_data, f, indent=2)
        
        print(f"✓ Created queue at: {queue_path}")
        result["queue_created"] = True
        
        # Run apply_updates manually
        apply_updates_script = Path(TEST_DIR) / "core" / "scripts" / "apply_updates.py"
        
        print(f"✓ Running apply_updates.py...")
        proc = subprocess.run(
            ["python3", str(apply_updates_script), TEST_DIR],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print("\nApply Updates Output:")
        print("-" * 60)
        print(proc.stdout)
        if proc.stderr:
            print("Errors:")
            print(proc.stderr)
        print("-" * 60)
        
        result["apply_updates_ran"] = True
        
        # Verify: Check if extension was installed
        ext_path = Path(TEST_DIR) / "extensions" / "generalbyte"
        result["extension_installed"] = ext_path.exists()
        
        if result["extension_installed"]:
            print(f"\n✓ Extension installed at: {ext_path}")
            
            # Check for key files
            config_path = ext_path / "config.json"
            tools_dir = ext_path / "tools"
            readme_path = ext_path / "readme.md"
            
            files_found = []
            if config_path.exists():
                print(f"✓ Found config.json")
                files_found.append("config.json")
            if tools_dir.exists():
                print(f"✓ Found tools directory")
                files_found.append("tools/")
                # List tools
                tool_files = list(tools_dir.glob("*.py"))
                if tool_files:
                    print(f"  - Tools: {', '.join([f.name for f in tool_files])}")
            if readme_path.exists():
                print(f"✓ Found readme.md")
                files_found.append("readme.md")
            
            result["files_found"] = files_found
        else:
            print(f"\n✗ Extension not found at: {ext_path}")
        
        # Determine final status
        if all([
            result["queue_created"],
            result["apply_updates_ran"],
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
    
    return result


def main():
    """Run the test"""
    # Step 1: Reset environment
    reset_environment()
    
    # Step 2: Download generalbyte extension
    result = test_download_generalbyte()
    
    # Output JSON results
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()



