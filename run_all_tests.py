"""
Luna Personal Assistant - Comprehensive MCP Server Test Suite

This master test script runs comprehensive tests for all MCP servers in the project:
- ChefByte: Kitchen and meal management system with SQLite database
- CoachByte: Workout tracking system with PostgreSQL database  
- GeneralByte: Home Assistant integration for notifications and todo management

Each test suite uses OpenAI Agents SDK with GPT-4.1 and includes:
- CRUD testing with before/after state comparison
- LLM judging for automated evaluation
- Comprehensive tool coverage
- Error handling and edge case testing
- Database reset to sample data before testing

Results are saved as JSON files and human-readable evaluation reports.
"""

import subprocess
import sys
import json
import os
import time
import traceback
from datetime import datetime
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Test configuration
TEST_AGENTS = [
    {
        "name": "ChefByte",
        "script": "chefbyte/test_agent.py",
        "description": "Kitchen and meal management system (SQLite)",
        "database": "SQLite",
        "timeout": 600  # 10 minutes
    },
    {
        "name": "CoachByte", 
        "script": "coachbyte/test_agent.py",
        "description": "Workout tracking system (PostgreSQL)",
        "database": "PostgreSQL",
        "timeout": 600  # 10 minutes
    },
    {
        "name": "GeneralByte",
        "script": "generalbyte/test_agent.py", 
        "description": "Home Assistant integration (no database)",
        "database": "None",
        "timeout": 300  # 5 minutes
    }
]

def print_banner():
    """Print test suite banner"""
    print("=" * 80)
    print("LUNA PERSONAL ASSISTANT - COMPREHENSIVE MCP SERVER TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing {len(TEST_AGENTS)} MCP servers with OpenAI Agents SDK + GPT-4.1")
    print()
    
    for agent in TEST_AGENTS:
        print(f"  • {agent['name']}: {agent['description']}")
    print()

def run_single_test(agent_config: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test agent and capture results"""
    name = agent_config["name"]
    script = agent_config["script"]
    timeout = agent_config["timeout"]
    
    print(f"🏃 Running {name} tests...")
    start_time = time.time()
    
    try:
        # Run the test script with timeout
        proc = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Determine success/failure
        success = proc.returncode == 0
        status = "✅ PASSED" if success else "❌ FAILED"
        
        result = {
            "agent": name,
            "script": script,
            "description": agent_config["description"],
            "database": agent_config["database"],
            "success": success,
            "returncode": proc.returncode,
            "duration": f"{duration:.2f}s",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat()
        }
        
        print(f"   {status} ({duration:.1f}s)")
        
        return result
        
    except subprocess.TimeoutExpired:
        print(f"   ⏰ TIMEOUT after {timeout}s")
        return {
            "agent": name,
            "script": script,
            "description": agent_config["description"],
            "database": agent_config["database"],
            "success": False,
            "returncode": -1,
            "duration": f"{timeout}s (timeout)",
            "stdout": "",
            "stderr": f"Test timed out after {timeout} seconds",
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.now().isoformat(),
            "timeout": True
        }
    except Exception as e:
        print(f"   💥 ERROR: {str(e)}")
        return {
            "agent": name,
            "script": script,
            "description": agent_config["description"],
            "database": agent_config["database"],
            "success": False,
            "returncode": -2,
            "duration": "error",
            "stdout": "",
            "stderr": f"Test execution error: {str(e)}",
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "error": str(e)
        }

def run_tests_parallel() -> List[Dict[str, Any]]:
    """Run all tests in parallel with proper resource management"""
    print("Running tests in parallel...\n")
    
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all test jobs
        future_to_agent = {
            executor.submit(run_single_test, agent): agent 
            for agent in TEST_AGENTS
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_agent):
            agent_config = future_to_agent[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"💥 Failed to get result for {agent_config['name']}: {e}")
                results.append({
                    "agent": agent_config["name"],
                    "script": agent_config["script"],
                    "success": False,
                    "error": f"Future execution error: {str(e)}"
                })
    
    return results

def run_tests_sequential() -> List[Dict[str, Any]]:
    """Run all tests sequentially (fallback option)"""
    print("Running tests sequentially...\n")
    
    results = []
    for agent_config in TEST_AGENTS:
        result = run_single_test(agent_config)
        results.append(result)
        print()  # Add spacing between tests
    
    return results

def generate_summary_report(results: List[Dict[str, Any]]) -> str:
    """Generate human-readable summary report"""
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get("success", False))
    failed_tests = total_tests - passed_tests
    
    # Calculate total duration
    total_duration = 0
    for result in results:
        duration_str = result.get("duration", "0s")
        if duration_str.endswith("s"):
            try:
                if "(timeout)" in duration_str:
                    duration_num = float(duration_str.split("s")[0])
                else:
                    duration_num = float(duration_str[:-1])
                total_duration += duration_num
            except:
                pass
    
    report = []
    report.append("=" * 80)
    report.append("LUNA PERSONAL ASSISTANT - TEST SUITE SUMMARY REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total Duration: {total_duration:.1f} seconds")
    report.append(f"Tests Run: {total_tests}")
    report.append(f"Passed: {passed_tests}")
    report.append(f"Failed: {failed_tests}")
    report.append(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    report.append("")
    
    # Individual test results
    report.append("INDIVIDUAL TEST RESULTS:")
    report.append("-" * 40)
    
    for result in results:
        name = result["agent"]
        status = "PASS" if result.get("success", False) else "FAIL"
        duration = result.get("duration", "unknown")
        description = result.get("description", "")
        database = result.get("database", "")
        
        report.append(f"{name} ({database}): {status} ({duration})")
        report.append(f"  {description}")
        
        if not result.get("success", False):
            stderr = result.get("stderr", "").strip()
            if stderr:
                # Show first few lines of error
                error_lines = stderr.split('\n')[:3]
                for line in error_lines:
                    if line.strip():
                        report.append(f"  ERROR: {line.strip()}")
        report.append("")
    
    # Files generated
    report.append("FILES GENERATED:")
    report.append("-" * 40)
    report.append("• master_test_results.json - Complete test results data")
    report.append("• master_test_summary.txt - This summary report")
    
    # Individual agent files
    for agent in TEST_AGENTS:
        name = agent["name"].lower()
        report.append(f"• {name}_test_results.json - {agent['name']} detailed results")
        report.append(f"• {name}_test_evaluation.txt - {agent['name']} LLM evaluation")
        
    report.append("")
    report.append("Next Steps:")
    report.append("- Review individual test evaluations for detailed analysis")
    report.append("- Check failed tests and fix any issues identified")
    report.append("- Re-run specific test agents if needed")
    
    if failed_tests > 0:
        report.append("")
        report.append("⚠️  ATTENTION: Some tests failed. Review error details above.")
    else:
        report.append("")
        report.append("🎉 ALL TESTS PASSED! MCP servers are functioning correctly.")
    
    return "\n".join(report)

def save_results(results: List[Dict[str, Any]]):
    """Save test results to files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save complete results as JSON
    results_file = "master_test_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "passed": sum(1 for r in results if r.get("success", False)),
            "failed": sum(1 for r in results if not r.get("success", False)),
            "results": results
        }, f, indent=2, default=str)
    
    # Generate and save summary report
    summary = generate_summary_report(results)
    summary_file = "master_test_summary.txt"
    with open(summary_file, "w") as f:
        f.write(summary)
    
    print(f"📁 Results saved to:")
    print(f"   • {results_file}")
    print(f"   • {summary_file}")

def main():
    """Main test execution function"""
    try:
        print_banner()
        
        # Run tests (try parallel first, fall back to sequential)
        try:
            results = run_tests_parallel()
        except Exception as e:
            print(f"⚠️  Parallel execution failed: {e}")
            print("Falling back to sequential execution...\n")
            results = run_tests_sequential()
        
        # Save results
        save_results(results)
        
        # Print summary
        print("\n" + "=" * 80)
        summary = generate_summary_report(results)
        print(summary)
        
        # Return appropriate exit code
        all_passed = all(r.get("success", False) for r in results)
        return 0 if all_passed else 1
        
    except KeyboardInterrupt:
        print("\n🛑 Test suite interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
