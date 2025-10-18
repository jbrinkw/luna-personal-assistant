Phase 1 Testing Strategy + Phase 1A Details

---

## Testing Strategy Overview

### Goal
Build entire backend system testable via API before any UI work. AI agents can interact purely through HTTP endpoints and file system verification.

### What We Can Build/Test Without UI

✅ **~90% of the system**:
- Supervisor (process management, health checks, port assignment)
- Config system (master_config, extension configs, sync)
- Extension lifecycle (install/update/delete via queue)
- Tool discovery and loading
- Agent API server
- MCP server
- Extension services
- Key manager (.env operations)
- Apply updates script

❌ **Requires UI** (Phase 2+):
- Extension Manager visual interface
- Store browsing
- Hub UI aggregation
- Extension iframing

---

## Reset Mechanism

### Pristine State Repository

**Location**: `/opt/luna-pristine/`

**Contents**:
```
/opt/luna-pristine/
├── luna.sh
├── core/
│   ├── agents/
│   ├── utils/
│   └── scripts/
├── supervisor/
│   ├── supervisor.py
│   └── api.py
├── extensions/
│   └── (empty)
├── hub_ui/
├── .env (with test secrets)
├── requirements.txt
└── README.md
Purpose: Git repository with minimal working Luna, used as template for test environment.
Test Environment
Location: /opt/luna-test/
Purpose: Working directory for running tests. Gets completely reset from pristine before each test suite.
Reset Process
Script: tests/reset_1a.sh
bash#!/bin/bash
# Stop any running Luna processes
pkill -f luna.sh
pkill -f supervisor.py
sleep 2

# Clean test directory
rm -rf /opt/luna-test

# Copy pristine to test
cp -r /opt/luna-pristine /opt/luna-test

# Ready for tests
echo "Environment reset complete"
When to run:

Before each test suite (mandatory)
Not needed between tests within same suite (unless test breaks state)


Test Execution Model
Test Suite Independence
Test suites (can run in any order after reset):

Each suite tests one subsystem
Suite has: setup → tests → teardown
Tests within suite CAN depend on each other (run sequentially)
Between suites: full reset required

Test Output Format
JSON structure (for AI grading or automatic validation):
json{
  "suite": "config_operations",
  "test": "create_master_config",
  "status": "pass|fail",
  "expected": "master_config.json created with default structure",
  "actual": "master_config.json exists, contains luna.version field",
  "details": "...",
  "timestamp": "2025-10-17T14:30:00Z"
}
```

### Grading Options

**Option 1: Automatic** (preferred where possible):
- Tests check files/APIs themselves
- Pass/fail determined by assertions
- Fast, reliable

**Option 2: AI-graded**:
- Tests output structured results
- AI agent reviews and grades based on expectations
- Better for complex scenarios

**Recommendation**: Use automatic where possible, AI-graded for complex scenarios.

---

## Phase 1 Architecture

### Phase 1A: Foundation (Week 1)

**Components**:
1. Bootstrap script
2. Supervisor basics (startup, shutdown, API)
3. Master config initialization
4. State.json management
5. Port assignment system

**Testable via**:
- HTTP requests to supervisor API
- File system verification
- Process inspection (ps, pgrep)

### Phase 1B: Config & Sync (Week 1-2)

**Components**:
1. Config sync script
2. Extension config operations
3. Tool config operations
4. Generic key matching

**Testable via**:
- File manipulation
- API calls to trigger sync
- JSON comparison

### Phase 1C: Extension Lifecycle (Week 2-3)

**Components**:
1. Update queue operations
2. Apply updates script
3. Install/update/delete operations
4. Dependency installation

**Testable via**:
- Queue API endpoints
- File system state before/after
- Git operations verification

### Phase 1D: Tool System (Week 3)

**Components**:
1. Tool discovery
2. Tool loading
3. Tool validation
4. MCP exposure filtering

**Testable via**:
- API endpoint returning discovered tools
- Tool execution tests
- MCP endpoint queries

### Phase 1E: Core Services (Week 3-4)

**Components**:
1. Agent API server
2. MCP server
3. Extension service lifecycle
4. Health monitoring

**Testable via**:
- API requests to Agent API
- MCP SSE connection tests
- Service health checks
- Process management verification

### Phase 1F: Integration (Week 4)

**Components**:
1. End-to-end extension installation
2. Multi-service coordination
3. Full restart cycle
4. Error handling and recovery

**Testable via**:
- Complete workflows
- Chaos testing (kill processes)
- Invalid input handling

---

## Phase 1A Detailed Breakdown

### Milestone 1A.1: Bootstrap + Supervisor Startup

**Build**:
- `luna.sh` (bootstrap script)
- `supervisor/supervisor.py` (minimal: startup, health endpoint)
- Default `master_config.json` generation
- Default `state.json` generation

**API Endpoints**:
```
GET /health
  Returns: {"status": "healthy"}

GET /services/status
  Returns: state.json contents

GET /ports
  Returns: port mappings
Test Cases for Milestone 1A.1
Test 1A.1.1: Supervisor Starts
yamlTest ID: 1A.1.1
Name: Supervisor Starts
Type: Automatic

Setup:
  - Run: ./tests/reset_1a.sh
  - Verify pristine state copied

Action:
  - Change to /opt/luna-test
  - Run: ./luna.sh &
  - Wait 5 seconds

Verify:
  - Process exists: pgrep -f supervisor.py returns PID
  - HTTP GET http://127.0.0.1:9999/health returns 200
  - File exists: supervisor/state.json
  - state.json is valid JSON

Expected Output:
  {
    "test": "1A.1.1_supervisor_starts",
    "status": "pass",
    "process_running": true,
    "process_pid": 12345,
    "health_check": 200,
    "state_file_exists": true,
    "state_file_valid_json": true
  }

Pass Criteria:
  - All boolean fields are true
  - health_check is 200
  - process_pid is positive integer
Test 1A.1.2: Master Config Auto-Creation
yamlTest ID: 1A.1.2
Name: Master Config Auto-Creation
Type: Automatic

Setup:
  - Run: ./tests/reset_1a.sh
  - Verify core/master_config.json does NOT exist

Action:
  - Start supervisor via bootstrap
  - Wait 5 seconds

Verify:
  - File exists: core/master_config.json
  - JSON is valid
  - Contains keys: luna, extensions, tool_configs, port_assignments
  - luna.version matches regex: \d{2}-\d{2}-\d{2}
  - extensions is empty object {}
  - tool_configs is empty object {}
  - port_assignments has extensions and services as empty objects

Expected Output:
  {
    "test": "1A.1.2_master_config_creation",
    "status": "pass",
    "file_exists": true,
    "valid_json": true,
    "has_required_keys": true,
    "version_format": "MM-DD-YY",
    "version_value": "10-17-25",
    "extensions_empty": true,
    "tool_configs_empty": true,
    "port_assignments_correct": true
  }

Pass Criteria:
  - All boolean fields are true
  - version_format is "MM-DD-YY"
Test 1A.1.3: Bootstrap Restart After Supervisor Crash
yamlTest ID: 1A.1.3
Name: Bootstrap Restart After Supervisor Crash
Type: Automatic

Setup:
  - Start system normally
  - Record initial supervisor PID

Action:
  - Kill supervisor: pkill -9 -f supervisor.py
  - Wait 15 seconds (3 health checks + buffer)

Verify:
  - New supervisor process exists
  - New PID is different from old PID
  - Health endpoint responds 200
  - state.json exists and is updated

Expected Output:
  {
    "test": "1A.1.3_bootstrap_restart",
    "status": "pass",
    "supervisor_restarted": true,
    "old_pid": 12345,
    "new_pid": 12389,
    "pids_different": true,
    "health_restored": true,
    "state_updated": true
  }

Pass Criteria:
  - supervisor_restarted is true
  - pids_different is true
  - health_restored is true
Test 1A.1.4: Bootstrap Health Check Loop
yamlTest ID: 1A.1.4
Name: Bootstrap Health Check Loop
Type: Automatic (with mock)

Setup:
  - Start system normally
  - Record initial supervisor PID

Action:
  - Modify supervisor to return 500 on /health
    (or use mock/test endpoint)
  - Wait 35 seconds (3 failed checks + buffer)

Verify:
  - Bootstrap killed supervisor (old PID gone)
  - New supervisor started (new PID exists)
  - New supervisor has clean health (returns 200)

Expected Output:
  {
    "test": "1A.1.4_health_check_loop",
    "status": "pass",
    "supervisor_killed": true,
    "supervisor_restarted": true,
    "health_restored": true,
    "old_pid_gone": true,
    "new_pid_present": true
  }

Pass Criteria:
  - All boolean fields are true
```

---

### Milestone 1A.2: Port Assignment System

**Build**:
- Port assignment logic in supervisor
- Port persistence in master_config
- Port reuse on restart

**API Endpoints**:
```
POST /ports/assign
  Body: {
    "type": "extension"|"service",
    "name": "string",
    "requires_port": true|false  (optional, for services)
  }
  Returns: {"port": 5200, "assigned": true}

GET /ports
  Returns: {
    "core": {...},
    "extensions": {...},
    "services": {...}
  }
Test Cases for Milestone 1A.2
Test 1A.2.1: Extension Port Assignment
yamlTest ID: 1A.2.1
Name: Extension Port Assignment
Type: Automatic

Setup:
  - Fresh system, no extensions
  - No ports assigned yet

Action:
  - POST /ports/assign {"type": "extension", "name": "notes"}
  - POST /ports/assign {"type": "extension", "name": "todos"}

Verify:
  - First response: port is 5200
  - Second response: port is 5201
  - GET /ports shows notes=5200, todos=5201
  - master_config.port_assignments.extensions updated correctly

Expected Output:
  {
    "test": "1A.2.1_extension_port_assignment",
    "status": "pass",
    "notes_port": 5200,
    "todos_port": 5201,
    "ports_sequential": true,
    "saved_to_master_config": true,
    "master_config_extensions": {
      "notes": 5200,
      "todos": 5201
    }
  }

Pass Criteria:
  - notes_port is 5200
  - todos_port is 5201
  - saved_to_master_config is true
Test 1A.2.2: Port Reuse After Restart
yamlTest ID: 1A.2.2
Name: Port Reuse After Restart
Type: Automatic

Setup:
  - Assign notes=5200, todos=5201
  - Verify saved to master_config

Action:
  - Restart supervisor (clean restart)
  - Wait for supervisor ready
  - GET /ports

Verify:
  - notes still has 5200
  - todos still has 5201
  - Ports unchanged from before restart

Expected Output:
  {
    "test": "1A.2.2_port_persistence",
    "status": "pass",
    "notes_port_stable": true,
    "todos_port_stable": true,
    "notes_port": 5200,
    "todos_port": 5201
  }

Pass Criteria:
  - Both stable flags are true
  - Port values match expected
Test 1A.2.3: Service Port Assignment with Key
yamlTest ID: 1A.2.3
Name: Service Port Assignment with Key
Type: Automatic

Setup:
  - Fresh system
  - No services assigned

Action:
  - POST /ports/assign {
      "type": "service",
      "name": "github_sync.webhook_receiver",
      "requires_port": true
    }

Verify:
  - Returns port from 5300+ range
  - Port saved to master_config.port_assignments.services
  - Key format is exactly "github_sync.webhook_receiver"
  - Key contains dot separator

Expected Output:
  {
    "test": "1A.2.3_service_port_assignment",
    "status": "pass",
    "port": 5300,
    "port_in_range": true,
    "key_format_correct": true,
    "key": "github_sync.webhook_receiver",
    "saved_to_master_config": true
  }

Pass Criteria:
  - port >= 5300
  - key_format_correct is true
  - saved_to_master_config is true
Test 1A.2.4: No Port for Service Without requires_port
yamlTest ID: 1A.2.4
Name: No Port for Service Without requires_port
Type: Automatic

Setup:
  - Fresh system

Action:
  - POST /ports/assign {
      "type": "service",
      "name": "email.worker",
      "requires_port": false
    }

Verify:
  - Returns port: null
  - Saved to master_config.port_assignments.services
  - Value in master_config is null (not missing)

Expected Output:
  {
    "test": "1A.2.4_service_no_port",
    "status": "pass",
    "port": null,
    "saved_as_null": true,
    "key_exists_in_config": true,
    "key": "email.worker"
  }

Pass Criteria:
  - port is null
  - saved_as_null is true
  - key_exists_in_config is true
```

---

### Milestone 1A.3: State Management

**Build**:
- State.json write operations
- State.json read operations
- State updates on service lifecycle

**API Endpoints**:
```
GET /services/status
  Returns: current state.json contents

POST /services/{name}/update-status
  Body: {
    "pid": 12345,
    "port": 5200,
    "status": "running"|"unhealthy"|"stopped"|"failed"
  }
  Returns: {"updated": true}
Test Cases for Milestone 1A.3
Test 1A.3.1: State Initialization
yamlTest ID: 1A.3.1
Name: State Initialization
Type: Automatic

Setup:
  - Fresh start
  - Delete supervisor/state.json if exists

Action:
  - Start supervisor

Verify:
  - state.json created in supervisor/ directory
  - Valid JSON
  - Has "services" key with object value
  - services object is initially empty

Expected Output:
  {
    "test": "1A.3.1_state_initialization",
    "status": "pass",
    "file_created": true,
    "valid_json": true,
    "has_services_key": true,
    "services_is_object": true,
    "services_initially_empty": true
  }

Pass Criteria:
  - All boolean fields are true
Test 1A.3.2: State Updates on Service Changes
yamlTest ID: 1A.3.2
Name: State Updates on Service Changes
Type: Automatic

Setup:
  - Supervisor running
  - state.json exists

Action:
  - POST /services/test_service/update-status {
      "pid": 99999,
      "port": 5200,
      "status": "running"
    }
  - GET /services/status

Verify:
  - test_service appears in state.json
  - Status is "running"
  - PID is 99999
  - Port is 5200
  - Response from GET matches

Expected Output:
  {
    "test": "1A.3.2_state_updates",
    "status": "pass",
    "service_added": true,
    "status_correct": true,
    "pid_correct": true,
    "port_correct": true,
    "service_data": {
      "pid": 99999,
      "port": 5200,
      "status": "running"
    }
  }

Pass Criteria:
  - All _correct fields are true
  - service_data matches expected values
Test 1A.3.3: State Persistence Across Restart
yamlTest ID: 1A.3.3
Name: State Persistence Across Restart
Type: Automatic

Setup:
  - Services running
  - state.json populated with test services

Action:
  - Record current state.json contents
  - Restart supervisor (graceful)
  - GET /services/status after restart

Verify:
  - state.json reloaded
  - Services still present
  - PIDs may change (services restart) but service entries exist

Expected Output:
  {
    "test": "1A.3.3_state_persistence",
    "status": "pass",
    "state_reloaded": true,
    "services_preserved": true,
    "service_count_matches": true
  }

Pass Criteria:
  - All boolean fields are true
```

---

## Test Runner Structure

### Directory Layout
```
tests/
├── phase_1a/
│   ├── test_1a1_supervisor_startup.py
│   ├── test_1a2_port_assignment.py
│   ├── test_1a3_state_management.py
│   └── run_all.py
├── reset_1a.sh
├── utils/
│   ├── http_client.py
│   ├── process_utils.py
│   └── file_utils.py
└── grader.py (optional AI grader)
Run All Tests Script
File: tests/phase_1a/run_all.py
python#!/usr/bin/env python3
"""
Run all Phase 1A tests and output structured results
"""
import json
import subprocess
import sys
from datetime import datetime

def main():
    results = {
        "suite": "phase_1a",
        "started_at": datetime.now().isoformat(),
        "tests": []
    }
    
    # Reset environment
    print("Resetting test environment...")
    subprocess.run(["./tests/reset_1a.sh"], check=True)
    
    # Run test modules
    test_modules = [
        "test_1a1_supervisor_startup",
        "test_1a2_port_assignment",
        "test_1a3_state_management"
    ]
    
    for module in test_modules:
        print(f"Running {module}...")
        result = subprocess.run(
            [sys.executable, "-m", f"tests.phase_1a.{module}"],
            capture_output=True,
            text=True
        )
        
        # Parse module output (JSON)
        module_results = json.loads(result.stdout)
        results["tests"].extend(module_results)
    
    # Calculate summary
    results["completed_at"] = datetime.now().isoformat()
    results["total_tests"] = len(results["tests"])
    results["passed"] = sum(1 for t in results["tests"] if t["status"] == "pass")
    results["failed"] = sum(1 for t in results["tests"] if t["status"] == "fail")
    
    # Output final results
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
Usage
bash# From /opt/luna-test directory
cd /opt/luna-test

# Run all Phase 1A tests
python tests/phase_1a/run_all.py > results_1a.json

# View results
cat results_1a.json | jq '.'

# Check if all passed
jq '.failed == 0' results_1a.json

Deliverables for Phase 1A
Code

 luna.sh (bootstrap script)
 supervisor/supervisor.py (basic version with startup, health endpoint)
 supervisor/api.py (API endpoints: /health, /services/status, /ports, /ports/assign)
 Port assignment logic
 State.json management functions
 Master config initialization logic

Tests

 11 test cases total:

4 for supervisor startup (Milestone 1A.1)
4 for port assignment (Milestone 1A.2)
3 for state management (Milestone 1A.3)


 tests/phase_1a/ directory with test scripts
 tests/reset_1a.sh reset script
 tests/phase_1a/run_all.py test runner
 tests/utils/ helper modules

Documentation

 Test execution instructions (README in tests/)
 Expected vs actual output format specification
 How to interpret test results
 Troubleshooting common test failures


Example Test Output
Successful test run:
json{
  "suite": "phase_1a",
  "started_at": "2025-10-17T14:30:00Z",
  "completed_at": "2025-10-17T14:35:00Z",
  "total_tests": 11,
  "passed": 11,
  "failed": 0,
  "tests": [
    {
      "test": "1A.1.1_supervisor_starts",
      "status": "pass",
      "duration_ms": 5200,
      "process_running": true,
      "process_pid": 12345,
      "health_check": 200
    },
    {
      "test": "1A.1.2_master_config_creation",
      "status": "pass",
      "duration_ms": 5100,
      "file_exists": true,
      "valid_json": true,
      "version_value": "10-17-25"
    }
  ]
}
Failed test run:
json{
  "suite": "phase_1a",
  "total_tests": 11,
  "passed": 10,
  "failed": 1,
  "tests": [
    {
      "test": "1A.2.2_port_persistence",
      "status": "fail",
      "duration_ms": 5300,
      "expected": "notes port should be 5200 after restart",
      "actual": "notes port is 5201 after restart",
      "error": "Port assignment not stable - ports changed after restart",
      "notes_port_stable": false,
      "notes_port": 5201
    }
  ]
}

Summary
Phase 1A builds:

Bootstrap process management
Supervisor core functionality
Port assignment with persistence
State management

Phase 1A tests:

11 comprehensive test cases
All testable via APIs and file system
Automatic grading where possible
Clean reset mechanism between suites

Next phases:

1B: Config & Sync
1C: Extension Lifecycle
1D: Tool System
1E: Core Services
1F: Integration