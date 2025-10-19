# Luna Phase 1B-F: Implementation and Test Plans

---

# Phase 1B: Config & Sync (Week 1-2)

## Overview

Build the configuration system that syncs user preferences from master_config to extension configs on disk.

---

## Milestone 1B.1: Config Sync Script

### Components to Build

**File**: `core/scripts/config_sync.py`

**Functionality**:
- Read master_config.json
- For each extension in master_config
- Load extension's config.json from disk
- Generic key matching (overwrite matching keys)
- Never overwrite "version" field
- Add "enabled" and "source" fields
- Write back to disk
- Sync tool configs similarly

**Helper Functions**:
```python
def load_master_config() -> dict
def load_extension_config(ext_name: str) -> dict
def save_extension_config(ext_name: str, config: dict)
def sync_single_extension(ext_name: str, master_data: dict)
def sync_tool_config(ext_name: str, master_tools: dict)
```

### API Endpoints

```
POST /config/sync
  Description: Manually trigger config sync
  Body: {} (no parameters)
  Returns: {
    "synced": ["notes", "todos"],
    "skipped": ["missing_extension"],
    "success": true
  }

GET /config/extension/{name}
  Description: Get merged config for an extension
  Returns: {
    "version": "10-17-25",
    "enabled": true,
    "source": "github:...",
    "max_notes": 1000,
    ...
  }
```

### Test Cases

**Test 1B.1.1: Basic Config Sync**

```yaml
Test ID: 1B.1.1
Name: Basic Config Sync
Type: Automatic

Setup:
  - Create master_config.json with:
    extensions.notes.config = {"max_notes": 1000, "theme": "dark"}
  - Create extensions/notes/config.json with:
    {"version": "10-17-25", "max_notes": 100, "theme": "light", "auto_save": true}

Action:
  - POST /config/sync

Verify:
  - extensions/notes/config.json updated
  - max_notes changed to 1000 (from master)
  - theme changed to "dark" (from master)
  - version still "10-17-25" (not overwritten)
  - auto_save still true (preserved, not in master)
  - enabled and source added from master

Expected Output:
  {
    "test": "1B.1.1_basic_config_sync",
    "status": "pass",
    "max_notes_updated": true,
    "theme_updated": true,
    "version_preserved": true,
    "auto_save_preserved": true,
    "enabled_added": true,
    "source_added": true,
    "final_config": {
      "version": "10-17-25",
      "max_notes": 1000,
      "theme": "dark",
      "auto_save": true,
      "enabled": true,
      "source": "github:user/notes"
    }
  }
```

**Test 1B.1.2: Missing Version Field Handling**

```yaml
Test ID: 1B.1.2
Name: Missing Version Field Handling
Type: Automatic

Setup:
  - Extension config has NO version field
  - Master config has notes extension

Action:
  - POST /config/sync

Verify:
  - Version field added to extension config
  - Version is current date in MM-DD-YY format
  - Regex: \d{2}-\d{2}-\d{2}

Expected Output:
  {
    "test": "1B.1.2_missing_version",
    "status": "pass",
    "version_added": true,
    "version_format_valid": true,
    "version_value": "10-17-25"
  }
```

**Test 1B.1.3: Tool Config Sync**

```yaml
Test ID: 1B.1.3
Name: Tool Config Sync
Type: Automatic

Setup:
  - Master config has:
    tool_configs.NOTES_CREATE_note = {"enabled_in_mcp": false, "passthrough": true}
  - Extension tools/tool_config.json has:
    {"NOTES_CREATE_note": {"enabled_in_mcp": true, "passthrough": false}}

Action:
  - POST /config/sync

Verify:
  - Tool config updated
  - enabled_in_mcp changed to false
  - passthrough changed to true

Expected Output:
  {
    "test": "1B.1.3_tool_config_sync",
    "status": "pass",
    "tool_config_updated": true,
    "enabled_in_mcp_correct": true,
    "passthrough_correct": true,
    "final_tool_config": {
      "enabled_in_mcp": false,
      "passthrough": true
    }
  }
```

**Test 1B.1.4: Skip Missing Extensions**

```yaml
Test ID: 1B.1.4
Name: Skip Missing Extensions
Type: Automatic

Setup:
  - Master config references "missing_extension"
  - Extension folder does not exist

Action:
  - POST /config/sync

Verify:
  - Sync completes without error
  - Missing extension skipped
  - Other extensions synced successfully
  - Returns skipped list

Expected Output:
  {
    "test": "1B.1.4_skip_missing",
    "status": "pass",
    "sync_completed": true,
    "no_errors": true,
    "skipped": ["missing_extension"],
    "synced": ["notes", "todos"]
  }
```

**Test 1B.1.5: Generic Key Matching**

```yaml
Test ID: 1B.1.5
Name: Generic Key Matching
Type: Automatic

Setup:
  - Extension config has: {"a": 1, "b": 2, "c": 3}
  - Master config has: {"b": 20, "d": 4}

Action:
  - POST /config/sync

Verify:
  - "a" preserved (not in master)
  - "b" updated to 20 (in master)
  - "c" preserved (not in master)
  - "d" NOT added (only keys in extension get updated, don't add new keys from master)

Expected Output:
  {
    "test": "1B.1.5_generic_matching",
    "status": "pass",
    "preserved_a": true,
    "updated_b": true,
    "preserved_c": true,
    "did_not_add_d": true,
    "final_config": {"a": 1, "b": 20, "c": 3}
  }
```

---

## Milestone 1B.2: Master Config Operations

### Components to Build

**API endpoints for master config manipulation**

### API Endpoints

```
GET /config/master
  Returns: Complete master_config.json

PUT /config/master
  Body: {complete master config}
  Returns: {"updated": true}

PATCH /config/master/extensions/{name}
  Body: {extension config data}
  Returns: {"updated": true}

PATCH /config/master/tool/{tool_name}
  Body: {"enabled_in_mcp": true, "passthrough": false}
  Returns: {"updated": true}
```

### Test Cases

**Test 1B.2.1: Read Master Config**

```yaml
Test ID: 1B.2.1
Name: Read Master Config
Type: Automatic

Setup:
  - Master config exists with known data

Action:
  - GET /config/master

Verify:
  - Returns complete master config
  - Has all sections: luna, extensions, tool_configs, port_assignments
  - Valid JSON

Expected Output:
  {
    "test": "1B.2.1_read_master",
    "status": "pass",
    "received_data": true,
    "has_all_sections": true,
    "valid_json": true
  }
```

**Test 1B.2.2: Update Extension in Master Config**

```yaml
Test ID: 1B.2.2
Name: Update Extension in Master Config
Type: Automatic

Setup:
  - Master config has notes extension

Action:
  - PATCH /config/master/extensions/notes
    Body: {"enabled": false, "config": {"max_notes": 2000}}

Verify:
  - Master config updated
  - notes.enabled = false
  - notes.config.max_notes = 2000
  - File written to disk

Expected Output:
  {
    "test": "1B.2.2_update_extension",
    "status": "pass",
    "master_config_updated": true,
    "enabled_correct": true,
    "config_correct": true,
    "persisted_to_disk": true
  }
```

**Test 1B.2.3: Update Tool Config in Master**

```yaml
Test ID: 1B.2.3
Name: Update Tool Config in Master
Type: Automatic

Setup:
  - Master config has tool configs

Action:
  - PATCH /config/master/tool/NOTES_CREATE_note
    Body: {"enabled_in_mcp": true, "passthrough": true}

Verify:
  - Tool config updated in master
  - Changes persisted

Expected Output:
  {
    "test": "1B.2.3_update_tool",
    "status": "pass",
    "tool_config_updated": true,
    "values_correct": true,
    "persisted": true
  }
```

---

## Reset Procedure for Phase 1B

**Script**: `tests/reset_1b.sh`

```bash
#!/bin/bash
# Stop Luna
pkill -f luna.sh
pkill -f supervisor.py
sleep 2

# Reset
rm -rf /opt/luna-test
cp -r /opt/luna-pristine /opt/luna-test

# Create test extensions for config sync tests
cd /opt/luna-test
mkdir -p extensions/notes/tools
mkdir -p extensions/todos

# Create sample configs
cat > extensions/notes/config.json << 'EOF'
{
  "version": "10-17-25",
  "max_notes": 100,
  "theme": "light",
  "auto_save": true,
  "required_secrets": ["OPENAI_API_KEY"]
}
EOF

cat > extensions/notes/tools/tool_config.json << 'EOF'
{
  "NOTES_CREATE_note": {
    "enabled_in_mcp": true,
    "passthrough": false
  }
}
EOF

echo "Phase 1B environment ready"
```

---

# Phase 1C: Extension Lifecycle (Week 2-3)

## Overview

Build the update queue system and apply_updates script for installing, updating, and deleting extensions.

---

## Milestone 1C.1: Update Queue Operations

### Components to Build

**API for queue management**

### API Endpoints

```
GET /queue/current
  Returns: Current update_queue.json or {"exists": false}

POST /queue/save
  Body: {
    "operations": [...],
    "master_config": {...}
  }
  Returns: {"saved": true}

DELETE /queue/current
  Returns: {"deleted": true}

GET /queue/status
  Returns: {
    "exists": true,
    "operation_count": 3,
    "operations": [
      {"type": "install", "target": "notes"},
      {"type": "update", "target": "todos"},
      {"type": "delete", "target": "old_ext"}
    ]
  }
```

### Test Cases

**Test 1C.1.1: Save Queue**

```yaml
Test ID: 1C.1.1
Name: Save Queue
Type: Automatic

Setup:
  - No queue exists

Action:
  - POST /queue/save with operations and master_config

Verify:
  - core/update_queue.json created
  - Valid JSON
  - Contains operations and master_config

Expected Output:
  {
    "test": "1C.1.1_save_queue",
    "status": "pass",
    "file_created": true,
    "valid_json": true,
    "has_operations": true,
    "has_master_config": true
  }
```

**Test 1C.1.2: Read Queue**

```yaml
Test ID: 1C.1.2
Name: Read Queue
Type: Automatic

Setup:
  - Create update_queue.json with known data

Action:
  - GET /queue/current

Verify:
  - Returns queue contents
  - Matches saved data

Expected Output:
  {
    "test": "1C.1.2_read_queue",
    "status": "pass",
    "queue_exists": true,
    "data_matches": true
  }
```

**Test 1C.1.3: Delete Queue**

```yaml
Test ID: 1C.1.3
Name: Delete Queue
Type: Automatic

Setup:
  - Queue exists

Action:
  - DELETE /queue/current

Verify:
  - File deleted
  - GET /queue/current returns {"exists": false}

Expected Output:
  {
    "test": "1C.1.3_delete_queue",
    "status": "pass",
    "file_deleted": true,
    "get_confirms_deleted": true
  }
```

---

## Milestone 1C.2: Apply Updates Script - Install Operations

### Components to Build

**File**: `core/scripts/apply_updates.py`

**Phase 3: Install Operations**
- Parse source string (github with/without subpath, upload)
- Git clone or unzip based on source
- Handle monorepo subpath extraction

### Test Cases

**Test 1C.2.1: Install from GitHub (Direct)**

```yaml
Test ID: 1C.2.1
Name: Install from GitHub Direct
Type: Automatic

Setup:
  - Create mock GitHub repo or use test fixture
  - Queue has install operation: {
      "type": "install",
      "source": "github:test-user/test-extension",
      "target": "test_ext"
    }

Action:
  - Run apply_updates.py manually (not via restart)

Verify:
  - extensions/test_ext/ exists
  - Contains expected files from repo
  - Git clone successful

Expected Output:
  {
    "test": "1C.2.1_install_github_direct",
    "status": "pass",
    "extension_installed": true,
    "directory_exists": true,
    "files_present": true
  }
```

**Test 1C.2.2: Install from GitHub (Monorepo Subpath)**

```yaml
Test ID: 1C.2.2
Name: Install from GitHub Monorepo
Type: Automatic

Setup:
  - Queue has install operation: {
      "type": "install",
      "source": "github:luna-extensions/luna-extensions:embedded/notes",
      "target": "notes"
    }

Action:
  - Run apply_updates.py

Verify:
  - extensions/notes/ exists
  - Contains only files from embedded/notes/ subfolder
  - Temp clone directory cleaned up

Expected Output:
  {
    "test": "1C.2.2_install_monorepo",
    "status": "pass",
    "extension_installed": true,
    "only_subfolder_copied": true,
    "temp_cleaned": true
  }
```

**Test 1C.2.3: Install from Upload**

```yaml
Test ID: 1C.2.3
Name: Install from Upload
Type: Automatic

Setup:
  - Create test zip file in /tmp/test_ext.zip
  - Queue has install operation: {
      "type": "install",
      "source": "upload:test_ext.zip",
      "target": "test_ext"
    }

Action:
  - Run apply_updates.py

Verify:
  - extensions/test_ext/ exists
  - Contains files from zip
  - Zip extracted correctly

Expected Output:
  {
    "test": "1C.2.3_install_upload",
    "status": "pass",
    "extension_installed": true,
    "files_extracted": true,
    "structure_correct": true
  }
```

---

## Milestone 1C.3: Apply Updates Script - Update/Delete Operations

### Components to Build

**Phase 2: Delete Operations**
**Phase 4: Update Operations**

### Test Cases

**Test 1C.3.1: Delete Extension**

```yaml
Test ID: 1C.3.1
Name: Delete Extension
Type: Automatic

Setup:
  - Extension "old_ext" exists in extensions/
  - Queue has delete operation: {
      "type": "delete",
      "target": "old_ext"
    }

Action:
  - Run apply_updates.py

Verify:
  - extensions/old_ext/ removed
  - Directory does not exist

Expected Output:
  {
    "test": "1C.3.1_delete_extension",
    "status": "pass",
    "extension_deleted": true,
    "directory_removed": true
  }
```

**Test 1C.3.2: Update Extension (Git)**

```yaml
Test ID: 1C.3.2
Name: Update Extension via Git
Type: Automatic

Setup:
  - Extension "notes" exists (git repo)
  - Create old file in extensions/notes/old_file.txt
  - Mock remote has changes (new commit)
  - Queue has update operation: {
      "type": "update",
      "source": "github:user/notes",
      "target": "notes"
    }

Action:
  - Run apply_updates.py

Verify:
  - Extension updated (git reset --hard)
  - Old uncommitted files removed
  - Latest commit checked out

Expected Output:
  {
    "test": "1C.3.2_update_git",
    "status": "pass",
    "extension_updated": true,
    "old_files_removed": true,
    "latest_commit": true
  }
```

**Test 1C.3.3: Update Extension (Upload)**

```yaml
Test ID: 1C.3.3
Name: Update Extension via Upload
Type: Automatic

Setup:
  - Extension "notes" exists
  - Create new zip with updated content
  - Queue has update operation: {
      "type": "update",
      "source": "upload:notes_v2.zip",
      "target": "notes"
    }

Action:
  - Run apply_updates.py

Verify:
  - Old extension removed
  - New version extracted
  - Files updated

Expected Output:
  {
    "test": "1C.3.3_update_upload",
    "status": "pass",
    "extension_updated": true,
    "old_removed": true,
    "new_installed": true
  }
```

---

## Milestone 1C.4: Apply Updates Script - Core Update

### Test Cases

**Test 1C.4.1: Core Update**

```yaml
Test ID: 1C.4.1
Name: Core Update
Type: Automatic

Setup:
  - Mock Luna core repo with changes in remote
  - Queue has core update operation: {
      "type": "update_core",
      "target_version": "10-20-25"
    }

Action:
  - Run apply_updates.py

Verify:
  - Core files updated (git reset --hard)
  - Core version changed in master_config
  - requirements.txt potentially updated

Expected Output:
  {
    "test": "1C.4.1_core_update",
    "status": "pass",
    "core_updated": true,
    "version_changed": true
  }
```

**Test 1C.4.2: Core Update Preserves User Extensions**

```yaml
Test ID: 1C.4.2
Name: Core Update Preserves Extensions
Type: Automatic

Setup:
  - User extensions "notes" and "todos" installed
  - Bundled extension "automation_memory" exists
  - Queue has core update

Action:
  - Run apply_updates.py with core update

Verify:
  - automation_memory updated (bundled, tracked by git)
  - notes/ preserved (user-installed, git-ignored)
  - todos/ preserved (user-installed, git-ignored)
  - Files in user extensions unchanged

Expected Output:
  {
    "test": "1C.4.2_core_preserves_extensions",
    "status": "pass",
    "bundled_updated": true,
    "notes_preserved": true,
    "todos_preserved": true,
    "notes_files_intact": true,
    "todos_files_intact": true
  }
```

---

## Milestone 1C.5: Apply Updates Script - Dependency Installation

### Components to Build

**Phase 6: Install All Dependencies**

### Test Cases

**Test 1C.5.1: Install Core Dependencies**

```yaml
Test ID: 1C.5.1
Name: Install Core Dependencies
Type: Automatic

Setup:
  - Fresh requirements.txt with known packages
  - Queue has any operation (triggers full dep install)

Action:
  - Run apply_updates.py

Verify:
  - pip install executed for core requirements.txt
  - Packages installed
  - pnpm install executed for hub_ui/ if exists

Expected Output:
  {
    "test": "1C.5.1_core_deps",
    "status": "pass",
    "pip_executed": true,
    "packages_installed": true,
    "pnpm_executed": true
  }
```

**Test 1C.5.2: Install Extension Dependencies**

```yaml
Test ID: 1C.5.2
Name: Install Extension Dependencies
Type: Automatic

Setup:
  - Extension with requirements.txt
  - Extension with ui/package.json
  - Extension with services/worker/requirements.txt

Action:
  - Run apply_updates.py

Verify:
  - pip install for extension requirements.txt
  - pnpm install for ui/
  - pip install for service requirements.txt

Expected Output:
  {
    "test": "1C.5.2_extension_deps",
    "status": "pass",
    "extension_pip_executed": true,
    "ui_pnpm_executed": true,
    "service_pip_executed": true
  }
```

---

## Milestone 1C.6: Full Update Cycle

### Test Cases

**Test 1C.6.1: Complete Update Flow**

```yaml
Test ID: 1C.6.1
Name: Complete Update Flow
Type: Integration

Setup:
  - Running system
  - Create queue with multiple operations

Action:
  - POST /restart (triggers update flow)
  - Wait for system shutdown
  - Wait for apply_updates to complete
  - Wait for system to restart

Verify:
  - All operations executed
  - Master config overwritten
  - Queue deleted
  - System restarts successfully
  - Extensions reflect changes

Expected Output:
  {
    "test": "1C.6.1_complete_flow",
    "status": "pass",
    "system_shutdown": true,
    "updates_applied": true,
    "queue_deleted": true,
    "system_restarted": true,
    "health_check_pass": true
  }
```

---

## Reset Procedure for Phase 1C

**Script**: `tests/reset_1c.sh`

```bash
#!/bin/bash
pkill -f luna.sh
pkill -f supervisor.py
sleep 2

rm -rf /opt/luna-test
cp -r /opt/luna-pristine /opt/luna-test

# Create test extensions
cd /opt/luna-test/extensions
mkdir -p test_ext old_ext notes todos

# Create sample extension structures
for ext in test_ext old_ext notes todos; do
  cat > $ext/config.json << EOF
{"version": "10-17-25", "name": "$ext"}
EOF
done

echo "Phase 1C environment ready"
```

---

# Phase 1D: Tool System (Week 3)

## Overview

Build tool discovery, loading, validation, and MCP exposure filtering.

---

## Milestone 1D.1: Tool Discovery

### Components to Build

**File**: `core/utils/tool_discovery.py`

**Functionality**:
- Scan all extensions
- Find tools/*_tools.py files
- Import and validate
- Extract TOOLS list and SYSTEM_PROMPT

### API Endpoints

```
GET /tools/discover
  Returns: {
    "tools": [
      {
        "name": "NOTES_CREATE_note",
        "extension": "notes",
        "file": "notes_tools.py",
        "system_prompt": "...",
        "enabled_in_mcp": true,
        "passthrough": false
      }
    ]
  }

GET /tools/list
  Returns: {
    "all": ["NOTES_CREATE_note", "NOTES_UPDATE_note"],
    "enabled_in_mcp": ["NOTES_CREATE_note"],
    "passthrough": []
  }
```

### Test Cases

**Test 1D.1.1: Discover Tools**

```yaml
Test ID: 1D.1.1
Name: Discover Tools
Type: Automatic

Setup:
  - Create extension with tools/notes_tools.py
  - Tools file has TOOLS list and valid functions

Action:
  - GET /tools/discover

Verify:
  - Returns list of discovered tools
  - Each tool has name, extension, file
  - Tool configs loaded

Expected Output:
  {
    "test": "1D.1.1_discover_tools",
    "status": "pass",
    "tools_found": 3,
    "tools": [
      {"name": "NOTES_CREATE_note", "extension": "notes"}
    ],
    "all_have_configs": true
  }
```

**Test 1D.1.2: Skip Invalid Tool Files**

```yaml
Test ID: 1D.1.2
Name: Skip Invalid Tool Files
Type: Automatic

Setup:
  - Extension with broken tools file (syntax error)
  - Extension with valid tools file

Action:
  - GET /tools/discover

Verify:
  - Broken file skipped
  - Valid tools still discovered
  - No crash

Expected Output:
  {
    "test": "1D.1.2_skip_invalid",
    "status": "pass",
    "discovery_completed": true,
    "valid_tools_found": 2,
    "invalid_skipped": 1,
    "no_errors": true
  }
```

---

## Milestone 1D.2: Tool Loading and Validation

### Components to Build

**Tool loader with Pydantic validation**

### API Endpoints

```
POST /tools/validate/{tool_name}
  Body: {tool arguments}
  Returns: {
    "valid": true,
    "errors": []
  }

POST /tools/execute/{tool_name}
  Body: {tool arguments}
  Returns: {
    "success": true,
    "result": "..."
  }
```

### Test Cases

**Test 1D.2.1: Validate Tool Arguments**

```yaml
Test ID: 1D.2.1
Name: Validate Tool Arguments
Type: Automatic

Setup:
  - Tool NOTES_CREATE_note with Pydantic args

Action:
  - POST /tools/validate/NOTES_CREATE_note
    Body: {"title": "Test", "content": "Hello"}

Verify:
  - Returns valid: true
  - No errors

Expected Output:
  {
    "test": "1D.2.1_validate_args",
    "status": "pass",
    "validation_passed": true,
    "no_errors": true
  }
```

**Test 1D.2.2: Reject Invalid Arguments**

```yaml
Test ID: 1D.2.2
Name: Reject Invalid Arguments
Type: Automatic

Setup:
  - Tool expects string, int

Action:
  - POST /tools/validate/NOTES_CREATE_note
    Body: {"title": 123, "content": null}

Verify:
  - Returns valid: false
  - Has error messages

Expected Output:
  {
    "test": "1D.2.2_reject_invalid",
    "status": "pass",
    "validation_failed": true,
    "has_errors": true,
    "error_count": 2
  }
```

**Test 1D.2.3: Execute Tool**

```yaml
Test ID: 1D.2.3
Name: Execute Tool
Type: Automatic

Setup:
  - Mock tool that returns test data

Action:
  - POST /tools/execute/TEST_TOOL
    Body: {valid arguments}

Verify:
  - Tool executed
  - Returns (success, result) tuple
  - Result as expected

Expected Output:
  {
    "test": "1D.2.3_execute_tool",
    "status": "pass",
    "execution_success": true,
    "result_received": true,
    "result_correct": true
  }
```

---

## Milestone 1D.3: MCP Tool Filtering

### Test Cases

**Test 1D.3.1: Filter by enabled_in_mcp**

```yaml
Test ID: 1D.3.1
Name: Filter MCP Enabled Tools
Type: Automatic

Setup:
  - 5 tools total
  - 3 with enabled_in_mcp: true
  - 2 with enabled_in_mcp: false

Action:
  - GET /tools/list?mcp_only=true

Verify:
  - Returns only 3 tools
  - All have enabled_in_mcp: true

Expected Output:
  {
    "test": "1D.3.1_filter_mcp",
    "status": "pass",
    "filtered_count": 3,
    "all_mcp_enabled": true
  }
```

**Test 1D.3.2: Passthrough Tool List**

```yaml
Test ID: 1D.3.2
Name: List Passthrough Tools
Type: Automatic

Setup:
  - Tools with passthrough: true/false mix

Action:
  - GET /tools/list?passthrough_only=true

Verify:
  - Returns only passthrough tools

Expected Output:
  {
    "test": "1D.3.2_passthrough_list",
    "status": "pass",
    "passthrough_count": 2,
    "all_passthrough": true
  }
```

---

## Reset Procedure for Phase 1D

**Script**: `tests/reset_1d.sh`

```bash
#!/bin/bash
pkill -f luna.sh
pkill -f supervisor.py
sleep 2

rm -rf /opt/luna-test
cp -r /opt/luna-pristine /opt/luna-test

# Create test extension with tools
cd /opt/luna-test
mkdir -p extensions/test_tools/tools

cat > extensions/test_tools/tools/test_tools.py << 'EOF'
from pydantic import BaseModel, Field
from typing import Tuple

SYSTEM_PROMPT = "Test tools"

class TEST_TOOL_Args(BaseModel):
    input: str = Field(...)

def TEST_TOOL(input: str) -> Tuple[bool, str]:
    """Test tool"""
    return (True, f"Result: {input}")

TOOLS = [TEST_TOOL]
EOF

cat > extensions/test_tools/tools/tool_config.json << 'EOF'
{
  "TEST_TOOL": {
    "enabled_in_mcp": true,
    "passthrough": false
  }
}
EOF

echo "Phase 1D environment ready"
```

---

# Phase 1E: Core Services (Week 3-4)

## Overview

Build Agent API server, MCP server, extension service lifecycle, and health monitoring.

---

## Milestone 1E.1: Agent API Server

### Components to Build

**File**: `core/utils/agent_api.py`

**Functionality**:
- OpenAI-compatible endpoints
- Chat completions
- Tool calling
- Streaming support

### API Endpoints

```
POST /v1/chat/completions
  Body: OpenAI format
  Returns: OpenAI format response

GET /v1/models
  Returns: {
    "models": [
      {"id": "gpt-4.1", "object": "model"},
      {"id": "claude-sonnet-4-5", "object": "model"}
    ]
  }

GET /healthz
  Returns: {"status": "healthy"}
```

### Test Cases

**Test 1E.1.1: Start Agent API**

```yaml
Test ID: 1E.1.1
Name: Start Agent API
Type: Automatic

Setup:
  - Supervisor running

Action:
  - Start Agent API via supervisor

Verify:
  - Process running on port 8080
  - Health endpoint responds
  - In state.json

Expected Output:
  {
    "test": "1E.1.1_start_agent_api",
    "status": "pass",
    "process_running": true,
    "health_check": 200,
    "port": 8080,
    "in_state": true
  }
```

**Test 1E.1.2: Chat Completion Request**

```yaml
Test ID: 1E.1.2
Name: Chat Completion Request
Type: Automatic

Setup:
  - Agent API running
  - Mock LLM or use real

Action:
  - POST /v1/chat/completions
    Body: {
      "model": "gpt-4.1",
      "messages": [{"role": "user", "content": "Hello"}]
    }

Verify:
  - Returns 200
  - Response has OpenAI format
  - Has choices array
  - Has message content

Expected Output:
  {
    "test": "1E.1.2_chat_completion",
    "status": "pass",
    "response_received": true,
    "format_valid": true,
    "has_content": true
  }
```

**Test 1E.1.3: Tool Calling**

```yaml
Test ID: 1E.1.3
Name: Tool Calling via Agent API
Type: Automatic

Setup:
  - Agent API with tools available

Action:
  - POST /v1/chat/completions with tool use

Verify:
  - Agent can call tools
  - Tool results returned
  - Response format correct

Expected Output:
  {
    "test": "1E.1.3_tool_calling",
    "status": "pass",
    "tool_called": true,
    "result_received": true,
    "format_correct": true
  }
```

---

## Milestone 1E.2: MCP Server

### Components to Build

**File**: `core/utils/mcp_server.py`

**Functionality**:
- SSE endpoint
- Bearer token auth
- Tool exposure
- Fast MCP protocol

### API Endpoints

```
GET /mcp/sse
  Headers: Authorization: Bearer {token}
  Returns: SSE stream

POST /mcp/tools/list
  Returns: Available tools

POST /mcp/tools/call
  Body: {tool, args}
  Returns: Tool result
```

### Test Cases

**Test 1E.2.1: Start MCP Server**

```yaml
Test ID: 1E.2.1
Name: Start MCP Server
Type: Automatic

Setup:
  - Supervisor running

Action:
  - Start MCP server

Verify:
  - Process on port 8765
  - Health check responds

Expected Output:
  {
    "test": "1E.2.1_start_mcp",
    "status": "pass",
    "process_running": true,
    "port": 8765
  }
```

**Test 1E.2.2: SSE Connection with Auth**

```yaml
Test ID: 1E.2.2
Name: SSE Connection with Auth
Type: Automatic

Setup:
  - MCP server running
  - Auth token in .env

Action:
  - GET /mcp/sse with Bearer token

Verify:
  - Connection established
  - SSE stream active

Expected Output:
  {
    "test": "1E.2.2_sse_auth",
    "status": "pass",
    "connection_established": true,
    "stream_active": true
  }
```

**Test 1E.2.3: Reject Invalid Auth**

```yaml
Test ID: 1E.2.3
Name: Reject Invalid Auth
Type: Automatic

Setup:
  - MCP server running

Action:
  - GET /mcp/sse with wrong/missing token

Verify:
  - Returns 401
  - Connection rejected

Expected Output:
  {
    "test": "1E.2.3_reject_auth",
    "status": "pass",
    "response_code": 401,
    "connection_rejected": true
  }
```

**Test 1E.2.4: List MCP Tools**

```yaml
Test ID: 1E.2.4
Name: List MCP Tools
Type: Automatic

Setup:
  - MCP server running
  - Tools with enabled_in_mcp: true

Action:
  - POST /mcp/tools/list

Verify:
  - Returns only MCP-enabled tools
  - Format correct

Expected Output:
  {
    "test": "1E.2.4_list_mcp_tools",
    "status": "pass",
    "tools_returned": 3,
    "all_mcp_enabled": true,
    "format_correct": true
  }
```

---

## Milestone 1E.3: Extension Service Lifecycle

### Test Cases

**Test 1E.3.1: Start Service with Port**

```yaml
Test ID: 1E.3.1
Name: Start Service with Port
Type: Automatic

Setup:
  - Extension with service requiring port

Action:
  - Supervisor starts service

Verify:
  - Service started with port argument
  - Process running
  - Port assigned in range 5300+
  - In state.json

Expected Output:
  {
    "test": "1E.3.1_start_service_port",
    "status": "pass",
    "service_started": true,
    "port_assigned": 5300,
    "process_running": true,
    "in_state": true
  }
```

**Test 1E.3.2: Start Service without Port**

```yaml
Test ID: 1E.3.2
Name: Start Service without Port
Type: Automatic

Setup:
  - Extension with service not requiring port

Action:
  - Supervisor starts service

Verify:
  - Service started without port arg
  - Process running
  - Port is null in state

Expected Output:
  {
    "test": "1E.3.2_start_service_no_port",
    "status": "pass",
    "service_started": true,
    "port_null": true,
    "process_running": true
  }
```

**Test 1E.3.3: Health Check Service**

```yaml
Test ID: 1E.3.3
Name: Health Check Service
Type: Automatic

Setup:
  - Service running with health endpoint

Action:
  - Wait for health check cycle (30+ seconds)

Verify:
  - Supervisor polled health endpoint
  - Status updated in state.json
  - Service marked as running

Expected Output:
  {
    "test": "1E.3.3_health_check",
    "status": "pass",
    "health_checked": true,
    "status_updated": true,
    "service_running": true
  }
```

**Test 1E.3.4: Restart Failed Service**

```yaml
Test ID: 1E.3.4
Name: Restart Failed Service
Type: Automatic

Setup:
  - Service with auto-restart enabled
  - Mock service to fail health checks

Action:
  - Wait for 2 failed health checks
  - Wait for restart logic

Verify:
  - Service stopped after 2 failures
  - Service restarted
  - New PID assigned

Expected Output:
  {
    "test": "1E.3.4_restart_failed",
    "status": "pass",
    "service_stopped": true,
    "service_restarted": true,
    "new_pid_assigned": true
  }
```

**Test 1E.3.5: Give Up After Max Restarts**

```yaml
Test ID: 1E.3.5
Name: Give Up After Max Restarts
Type: Automatic

Setup:
  - Service that always fails health

Action:
  - Let health check cycle run
  - Service restarts once, fails again
  - Service restarts twice, fails again

Verify:
  - After 2 restart attempts, status = "failed"
  - Supervisor stops trying
  - Service not running

Expected Output:
  {
    "test": "1E.3.5_max_restarts",
    "status": "pass",
    "status_failed": true,
    "supervisor_stopped_trying": true,
    "service_not_running": true
  }
```

---

## Reset Procedure for Phase 1E

**Script**: `tests/reset_1e.sh`

```bash
#!/bin/bash
pkill -f luna.sh
pkill -f supervisor.py
sleep 2

rm -rf /opt/luna-test
cp -r /opt/luna-pristine /opt/luna-test

# Create test service
cd /opt/luna-test
mkdir -p extensions/test_ext/services/test_service

cat > extensions/test_ext/services/test_service/service_config.json << 'EOF'
{
  "name": "test_service",
  "requires_port": true,
  "health_check": "/healthz",
  "restart_on_failure": true
}
EOF

cat > extensions/test_ext/services/test_service/start.sh << 'EOF'
#!/bin/bash
PORT=$1
python3 -m http.server $PORT
EOF

chmod +x extensions/test_ext/services/test_service/start.sh

# Set test auth token
echo "MCP_AUTH_TOKEN=test-token-12345" >> .env

echo "Phase 1E environment ready"
```

---

# Phase 1F: Integration (Week 4)

## Overview

End-to-end testing, multi-service coordination, chaos testing, error handling.

---

## Milestone 1F.1: End-to-End Extension Installation

### Test Cases

**Test 1F.1.1: Install Extension from Store**

```yaml
Test ID: 1F.1.1
Name: Full Extension Install Flow
Type: Integration

Setup:
  - Running system
  - Extension store with test extension

Action:
  - Create install operation in queue
  - Trigger restart
  - Wait for completion

Verify:
  - Extension installed
  - Dependencies installed
  - Config synced
  - Tools discovered
  - Service started (if any)
  - Health checks passing

Expected Output:
  {
    "test": "1F.1.1_full_install",
    "status": "pass",
    "extension_installed": true,
    "deps_installed": true,
    "config_synced": true,
    "tools_discovered": true,
    "services_started": true,
    "health_passing": true
  }
```

---

## Milestone 1F.2: Multi-Service Coordination

### Test Cases

**Test 1F.2.1: Multiple Extensions with Services**

```yaml
Test ID: 1F.2.1
Name: Multiple Extensions with Services
Type: Integration

Setup:
  - Install 3 extensions with services
  - Each has UI and background service

Action:
  - Start system

Verify:
  - All extensions started
  - All UIs on correct ports (5200, 5201, 5202)
  - All services on correct ports (5300, 5301, 5302)
  - All health checks passing
  - Port assignments stable

Expected Output:
  {
    "test": "1F.2.1_multi_service",
    "status": "pass",
    "extensions_count": 3,
    "all_uis_running": true,
    "all_services_running": true,
    "ports_correct": true,
    "health_all_pass": true
  }
```

---

## Milestone 1F.3: Chaos Testing

### Test Cases

**Test 1F.3.1: Kill Random Service**

```yaml
Test ID: 1F.3.1
Name: Kill Random Service
Type: Chaos

Setup:
  - System running with multiple services

Action:
  - Kill random service process
  - Wait for supervisor to detect and restart

Verify:
  - Supervisor detected failure
  - Service restarted
  - System stable
  - Other services unaffected

Expected Output:
  {
    "test": "1F.3.1_chaos_kill",
    "status": "pass",
    "failure_detected": true,
    "service_restarted": true,
    "system_stable": true
  }
```

**Test 1F.3.2: Corrupt Config File**

```yaml
Test ID: 1F.3.2
Name: Corrupt Config File
Type: Chaos

Setup:
  - Running system

Action:
  - Corrupt master_config.json (invalid JSON)
  - Restart supervisor

Verify:
  - Supervisor handles gracefully
  - Either: creates new default OR refuses to start with clear error
  - System doesn't crash

Expected Output:
  {
    "test": "1F.3.2_corrupt_config",
    "status": "pass",
    "handled_gracefully": true,
    "no_crash": true,
    "error_logged": true
  }
```

**Test 1F.3.3: Simultaneous Requests**

```yaml
Test ID: 1F.3.3
Name: Simultaneous API Requests
Type: Load

Setup:
  - System running

Action:
  - Send 100 concurrent requests to various APIs

Verify:
  - All requests handled
  - No crashes
  - Reasonable response times
  - No deadlocks

Expected Output:
  {
    "test": "1F.3.3_concurrent",
    "status": "pass",
    "all_handled": true,
    "no_crashes": true,
    "avg_response_ms": 150
  }
```

---

## Milestone 1F.4: Error Recovery

### Test Cases

**Test 1F.4.1: Invalid Queue Operation**

```yaml
Test ID: 1F.4.1
Name: Invalid Queue Operation
Type: Error Handling

Setup:
  - Create queue with invalid operation

Action:
  - Trigger restart

Verify:
  - apply_updates detects invalid operation
  - Logs error
  - Continues with valid operations
  - System recovers

Expected Output:
  {
    "test": "1F.4.1_invalid_queue",
    "status": "pass",
    "error_detected": true,
    "error_logged": true,
    "valid_ops_completed": true,
    "system_recovered": true
  }
```

**Test 1F.4.2: Dependency Install Failure**

```yaml
Test ID: 1F.4.2
Name: Dependency Install Failure
Type: Error Handling

Setup:
  - Extension with invalid requirements.txt

Action:
  - Install extension via queue

Verify:
  - Pip install fails
  - Error logged
  - Extension installed but deps not
  - System continues

Expected Output:
  {
    "test": "1F.4.2_dep_failure",
    "status": "pass",
    "install_failed": true,
    "error_logged": true,
    "extension_present": true,
    "system_stable": true
  }
```

---

## Reset Procedure for Phase 1F

**Script**: `tests/reset_1f.sh`

```bash
#!/bin/bash
pkill -f luna.sh
pkill -f supervisor.py
sleep 2

rm -rf /opt/luna-test
cp -r /opt/luna-pristine /opt/luna-test

# Create multiple test extensions
cd /opt/luna-test/extensions

for i in {1..3}; do
  mkdir -p ext$i/ui ext$i/services/worker
  
  cat > ext$i/config.json << EOF
{"version": "10-17-25", "name": "ext$i"}
EOF

  cat > ext$i/ui/start.sh << 'EOF'
#!/bin/bash
PORT=$1
python3 -m http.server $PORT
EOF
  chmod +x ext$i/ui/start.sh

  cat > ext$i/services/worker/service_config.json << EOF
{
  "name": "worker",
  "requires_port": true,
  "health_check": "/healthz",
  "restart_on_failure": true
}
EOF

  cat > ext$i/services/worker/start.sh << 'EOF'
#!/bin/bash
PORT=$1
python3 -m http.server $PORT
EOF
  chmod +x ext$i/services/worker/start.sh
done

echo "Phase 1F environment ready"
```

---

# Summary: All Phase 1 Test Counts

## Phase 1A: Foundation (11 tests)
- Milestone 1A.1: 4 tests (supervisor startup)
- Milestone 1A.2: 4 tests (port assignment)
- Milestone 1A.3: 3 tests (state management)

## Phase 1B: Config & Sync (8 tests)
- Milestone 1B.1: 5 tests (config sync)
- Milestone 1B.2: 3 tests (master config ops)

## Phase 1C: Extension Lifecycle (13 tests)
- Milestone 1C.1: 3 tests (queue operations)
- Milestone 1C.2: 3 tests (install operations)
- Milestone 1C.3: 3 tests (update/delete)
- Milestone 1C.4: 2 tests (core update)
- Milestone 1C.5: 2 tests (dependencies)
- Milestone 1C.6: 1 test (full flow)

## Phase 1D: Tool System (8 tests)
- Milestone 1D.1: 2 tests (discovery)
- Milestone 1D.2: 3 tests (loading/validation)
- Milestone 1D.3: 2 tests (MCP filtering)

## Phase 1E: Core Services (13 tests)
- Milestone 1E.1: 3 tests (Agent API)
- Milestone 1E.2: 4 tests (MCP server)
- Milestone 1E.3: 5 tests (service lifecycle)

## Phase 1F: Integration (8 tests)
- Milestone 1F.1: 1 test (E2E install)
- Milestone 1F.2: 1 test (multi-service)
- Milestone 1F.3: 3 tests (chaos)
- Milestone 1F.4: 2 tests (error recovery)

**Total Phase 1 Tests: 61 tests**

---

# Test Execution Order

1. Run Phase 1A → Foundation must work first
2. Run Phase 1B → Config system needed for later phases
3. Run Phase 1C → Extension lifecycle needed for phases D-F
4. Run Phase 1D → Tool system isolated, can run anytime after 1C
5. Run Phase 1E → Core services need everything else
6. Run Phase 1F → Integration tests everything together

Each phase has independent reset script. Full reset between phases.

---

# Next Steps

This gives you complete implementation and test plans for all of Phase 1. Each milestone is:
- ✅ Clearly defined
- ✅ API testable
- ✅ Has specific test cases
- ✅ Has reset procedures
- ✅ Has pass/fail criteria

Ready to build Phase 1A through 1F with confidence that every component is thoroughly testable via APIs!