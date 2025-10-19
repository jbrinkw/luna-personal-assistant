#!/usr/bin/env python3
"""
Run all Phase 1C tests and output structured results
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def reset_environment():
    """Reset test environment"""
    print("=" * 60)
    print("Resetting test environment...")
    print("=" * 60)
    
    reset_script = Path(__file__).parent.parent / "reset_phase1.sh"
    result = subprocess.run(
        ["bash", str(reset_script)],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("Warning: Reset script had non-zero exit code")
    print()


def run_test_module(module_name):
    """Run a test module and return results"""
    print(f"Running {module_name}...")
    print("-" * 60)
    
    module_path = Path(__file__).parent / f"{module_name}.py"
    
    result = subprocess.run(
        [sys.executable, str(module_path)],
        capture_output=True,
        text=True,
        timeout=180  # Longer timeout for full cycle test
    )
    
    # Print stdout for visibility
    print(result.stdout)
    
    # Try to parse JSON from last line
    try:
        # Find JSON in output
        lines = result.stdout.strip().split('\n')
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith('['):
                json_str = '\n'.join(lines[i:])
                return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing test results: {e}")
        return []
    
    return []


def main():
    """Run all Phase 1C tests"""
    results = {
        "suite": "phase_1c",
        "started_at": datetime.now().isoformat(),
        "tests": []
    }
    
    print("=" * 60)
    print("PHASE 1C TEST SUITE")
    print("=" * 60)
    print()
    
    # Reset environment
    reset_environment()
    
    # Test modules in order
    test_modules = [
        "test_1c1_queue",
        "test_1c2_install",
        "test_1c3_delete_update",
        "test_1c5_dependencies",
        "test_1c6_full_cycle"
    ]
    
    for module in test_modules:
        try:
            module_results = run_test_module(module)
            results["tests"].extend(module_results)
        except subprocess.TimeoutExpired:
            print(f"ERROR: {module} timed out")
            results["tests"].append({
                "test": module,
                "status": "timeout",
                "error": "Test module timed out after 180 seconds"
            })
        except Exception as e:
            print(f"ERROR: {module} failed with exception: {e}")
            results["tests"].append({
                "test": module,
                "status": "error",
                "error": str(e)
            })
        print()
    
    # Calculate summary
    results["completed_at"] = datetime.now().isoformat()
    results["total_tests"] = len(results["tests"])
    results["passed"] = sum(1 for t in results["tests"] if t.get("status") == "pass")
    results["failed"] = sum(1 for t in results["tests"] if t.get("status") == "fail")
    results["errors"] = sum(1 for t in results["tests"] if t.get("status") in ["error", "timeout"])
    
    # Print summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Errors: {results['errors']}")
    print("=" * 60)
    print()
    
    # Output full results as JSON
    print("=" * 60)
    print("FULL RESULTS (JSON)")
    print("=" * 60)
    print(json.dumps(results, indent=2))
    
    # Return exit code based on results
    if results["failed"] > 0 or results["errors"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()



