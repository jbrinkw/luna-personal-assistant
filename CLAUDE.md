
# Luna Project Schema Definition (v14, MVP-integrated)

Single-source spec with the latest cuts. Minimal, runnable.

---

## 0) Snapshot

* **Services** (each its own process): **Hub UI**, **MCP Server**, **Agent API**.
* **Servers location (for now)**: both **Agent API** and **MCP Server** are single-file modules under `core/utils/`.
* **Auth**: Hub UI + Agent API = localhost only (no auth). MCP = Bearer token.
* **LLM**: default **gpt-4.1** via selector module.
* **Agents**: `simple_agent` (LangChain ReAct), `passthrough_agent` (includes internal **DIRECT_RESPONSE** tool to answer non-tool prompts naturally).
* **Tools**: Python callables, **Pydantic-validated I/O**, opt-in MCP exposure.
* **Memory/Automation**: **Postgres** (UTC in DB; display in **America/New_York**). **Memories = list[str]** (no scopes).
* **Python deps**: **`requirements.txt`**.
* **Secrets**: `.env` in repo root.
* **Agent discovery**: agents discovered at **Hub UI startup** and selectable in UIs (flows/schedules).
* **Extension services**: background processes/servers auto-discovered from `services/` folders.
* **Auto-update**: field present in extension schema, **not implemented** in MVP.

Default ports: Hub UI `5173`, Agent API `8080`, MCP `8765`, Extension UIs `5200–5299`, Extension Services `5300–5399`. Bind `127.0.0.1`.

---

## 1) Project Directory Structure

```
luna/
|-- core/
|   |-- agents/
|   |   |-- simple_agent/
|   |   |-- passthrough_agent/
|   |
|   |-- utils/
|   |   |-- agent_api.py
|   |   |-- mcp_server.py
|   |   |-- llm_selector.py
|   |   |-- prompt_runner.py
|   |   |-- db.py
|   |   |-- service_manager.py
|   |
|   |-- scripts/
|       |-- start_all.sh
|
|-- extensions/
|   |-- automation_memory/
|   |   |-- readme.md
|   |   |-- config.json
|   |   |-- requirements.txt
|   |   |-- tools/
|   |   |   |-- tool_config.json
|   |   |   |-- automation_memory_tools.py
|   |   |-- ui/
|   |       |-- package.json
|   |       |-- start.sh
|   |       |-- (ui files…)
|   |
|   |-- my_awesome_extension/
|       |-- readme.md
|       |-- config.json
|       |-- requirements.txt
|       |-- tools/
|       |   |-- tool_config.json
|       |   |-- my_awesome_tools.py
|       |-- ui/
|       |   |-- package.json
|       |   |-- start.sh
|       |   |-- (ui files…)
|       |-- services/
|           |-- my_background_worker/
|           |   |-- start.sh
|           |   |-- service_config.json
|           |   |-- (service files…)
|           |-- sync_daemon/
|               |-- start.sh
|               |-- service_config.json
|               |-- (service files…)
|
|-- hub_ui/
|
|-- .env
|-- requirements.txt
|-- README.md
```

---

## 2) The Hub & Core Systems

### Hub UI

* **Extension management**: load by **local path** or **GitHub URL**. The `auto_update` flag exists but is not implemented.
* **UI aggregation**: for each extension, Hub launches `ui/start.sh <port>`, then iframes it.
* **Service management**: for each extension, Hub discovers and launches services from `services/` folders.
* **Navigation**: main menu lists active extension UIs, services, and their health.
* **Env/secret checks**: rendered on **each extension's page** using its `required_secrets`.
* **Agent discovery**: on startup, Hub discovers agents in `core/agents/` and exposes an **Agent dropdown** in **Task Flows** and **Scheduled Tasks**.
* **Health**: `/healthz`.

### MCP Server (Fast MCP + SSE)

* Exposes tools with `"enabled_in_mcp": true` from all active extensions.
* SSE endpoint (e.g., `/mcp/sse`), Bearer `MCP_AUTH_TOKEN`.
* Single process server module: `core/utils/mcp_server.py`.

### Agent API Server

* **Fully featured OpenAI-compatible server** exposed locally.
* Single file: `core/utils/agent_api.py`.

---

## 3) Extension Schema

### Loading

* **Local Path** or **GitHub URL**. `auto_update` remains in schema but is not implemented.

### Directory

```
<extension>/
|-- readme.md
|-- config.json
|-- requirements.txt
|-- tools/
|   |-- tool_config.json
|   |-- *_tools.py
|-- ui/
|   |-- package.json
|   |-- start.sh
|   |-- (ui files…)
|-- services/
    |-- <service_name>/
        |-- start.sh
        |-- service_config.json
        |-- (service files…)
```

### `config.json` (manifest — trimmed)

```json
{
  "name": "my_awesome_extension",
  "required_secrets": ["FOO_API_KEY", "BAR_URL"],
  "auto_update": false
}
```

* Each extension page shows a list of missing `required_secrets` from `.env`.

---

## 4) Tool Schema

### Naming

* `DOMAIN_{GET|UPDATE|ACTION}_VerbNoun`.

### Docstring (required)

1. One-sentence summary.
2. `Example Prompt:` natural language trigger.
3. `Example Response:` compact JSON-like output.
4. `Example Args:` JSON-like args.
5. `Notes:` (optional).

### File format (`*_tools.py`)

```python
from pydantic import BaseModel, Field
from typing import Tuple

SYSTEM_PROMPT = "The user has access to tools for managing their notes."

class NOTES_UPDATE_ProjectNoteArgs(BaseModel):
    project_id: str = Field(...)
    content: str = Field(...)

def NOTES_UPDATE_project_note(project_id: str, content: str) -> Tuple[bool, str]:
    """Append content to today's dated note entry for a project.
    Example Prompt: add "ship MVP" under "Milestones" for project Eco AI
    Example Response: {"project_id": "Eco AI", "success": true}
    Example Args: {"project_id": "string", "content": "string"}
    """
    try:
        _ = NOTES_UPDATE_ProjectNoteArgs(project_id=project_id, content=content)
        return (True, '{"success": true, "project_id": "' + project_id + '"}')
    except Exception as e:
        return (False, f"An error occurred: {e}")

TOOLS = [NOTES_UPDATE_project_note]
```

### `tool_config.json`

```json
{
  "NOTES_UPDATE_project_note": {
    "enabled_in_mcp": true,
    "passthrough": false
  }
}
```

* Inputs validated with **Pydantic** inside the tool.
* Return shape is always `(success: bool, content: str)`.
* Tool names include the extension name; no collision policy required.

---

## 5) UI Schema (Extensions)

* Install: detect `ui/package.json`, run `pnpm install` once.
* Start: run `ui/start.sh <port>`; must serve `/healthz` 200.
* Secret check UX: each extension page shows missing `required_secrets` inline.

---

## 6) Services Schema (Extensions)

### Discovery

* **Auto-discovery**: Hub scans `services/` at extension load time. Any subfolder containing `start.sh` is treated as a service.

### Directory Structure

```
<extension>/services/
|-- my_background_worker/
|   |-- start.sh
|   |-- service_config.json
|   |-- worker.py
|   |-- (other service files…)
|
|-- webhook_receiver/
    |-- start.sh
    |-- service_config.json
    |-- server.py
    |-- (other service files…)
```

### `service_config.json` (per-service metadata)

```json
{
  "name": "my_background_worker",
  "requires_port": true,
  "health_check": "/healthz",
  "restart_on_failure": true
}
```

**Fields:**
* `name`: Service identifier (string, required)
* `requires_port`: If `true`, Hub assigns port from range `5300–5399` and passes to `start.sh` (boolean, default `false`)
* `health_check`: Endpoint path to poll if `requires_port=true` (string, nullable)
* `restart_on_failure`: Auto-restart if health check fails (boolean, default `true`)

### `start.sh` Contract

```bash
#!/bin/bash
# Args: $1 = port (only if requires_port=true in service_config.json)
# Must bind to 127.0.0.1:$1 if port provided
# Must expose GET /healthz returning 200 if requires_port=true and health_check specified
```

### Port Assignment

* **Services range**: `5300–5399` (distinct from UI's `5200–5299`)
* Hub assigns sequentially, passes to `start.sh` as `$1`

### Lifecycle

1. **Discovery**: On extension activation, Hub finds all `services/*/service_config.json`
2. **Start**: Execute `start.sh <port>` for each service (port only if `requires_port=true`)
3. **Health monitoring**: Poll health endpoints every 30s; restart if `restart_on_failure=true`
4. **Stop**: On extension deactivation, SIGTERM all service processes

### Example: Queue Worker Service (no port)

```
extensions/email_processor/services/queue_worker/
|-- start.sh
|-- service_config.json
|-- worker.py
```

**service_config.json**:
```json
{
  "name": "queue_worker",
  "requires_port": false,
  "health_check": null,
  "restart_on_failure": true
}
```

**start.sh**:
```bash
#!/bin/bash
python worker.py  # no port needed, runs in background
```

### Example: Webhook Receiver Service (with port)

```
extensions/github_sync/services/webhook_receiver/
|-- start.sh
|-- service_config.json
|-- server.py
```

**service_config.json**:
```json
{
  "name": "webhook_receiver",
  "requires_port": true,
  "health_check": "/healthz",
  "restart_on_failure": true
}
```

**start.sh**:
```bash
#!/bin/bash
PORT=$1
python server.py --port $PORT  # binds to 127.0.0.1:$PORT
```

### Hub UI Services Tab

Each extension page shows a **Services** tab displaying:
* Service name and status (running/stopped/failed)
* Port (if assigned)
* Last health check timestamp
* Manual start/stop/restart buttons

---

## 7) Core Agents

### `simple_agent`

* LangChain **ReAct**; may call tools and synthesize results.

### `passthrough_agent`

* Honors `passthrough=true` tools.
* Provides **DIRECT_RESPONSE** internal tool to answer natural prompts with no tool call.

### Error/Retry

* On tool failure `(success=False)`, up to 2 corrective retries; else summarized failure.

### I/O Contract (conceptual)

```python
from pydantic import BaseModel
from typing import List, Optional, Literal

class Msg(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str

class AgentRequest(BaseModel):
    prompt: str
    chat_history: List[Msg] = []
    memory: List[str] = []

class AgentResult(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
```

---

## 8) Built-in Extension: `automation_memory`

**Features**

* **Memories**: append-only list of strings.
* **Scheduled Tasks**: cron-like prompts run via a **selected agent**.
* **Task Flows**: ordered prompts run via a **selected agent**.

**UI**

* Tabs: **Memories**, **Scheduled**, **Flows**.
* Agent dropdowns present in **Scheduled** and **Flows** (agents discovered at Hub startup).

---

## 9) Process Model, Ports, Network

* **Hub UI**: `127.0.0.1:5173`, no auth.
* **Agent API**: `127.0.0.1:8080`, no auth; CORS localhost.
* **MCP**: `127.0.0.1:8765`, Bearer `MCP_AUTH_TOKEN`, SSE at `/mcp/sse`.
* **Extension UIs**: `127.0.0.1:5200–5299`.
* **Extension Services**: `127.0.0.1:5300–5399`.

---

## 10) Agent API (summary only)

* A **fully featured OpenAI-compatible server** exposed locally, implemented as `core/utils/agent_api.py`.

---

## 11) MCP Server

* SSE endpoint (e.g., `/mcp/sse`) with Bearer `MCP_AUTH_TOKEN`.
* Discovers active extensions and exposes tools where `enabled_in_mcp=true`.

---

## 12) Database (Postgres)

* Store timestamps in UTC; display in `America/New_York`.


THIS IS THE REFACTOR GOAL
THIS IS THE REFACTOR GOAL
THIS IS THE REFACTOR GOAL

Complete MVP Specification1. Directory Structure/opt/luna/luna-repo/
├── luna.sh
├── core/
│   ├── master_config.json          (git-ignored)
│   ├── update_queue.json           (git-ignored)
│   ├── agents/
│   │   ├── simple_agent/
│   │   └── passthrough_agent/
│   ├── utils/
│   │   ├── agent_api.py
│   │   ├── mcp_server.py
│   │   ├── llm_selector.py
│   │   └── db.py
│   └── scripts/
│       ├── apply_updates.py
│       └── config_sync.py
├── supervisor/
│   ├── supervisor.py
│   ├── state.json                  (git-ignored)
│   └── api.py
├── extensions/
│   ├── automation_memory/
│   │   ├── config.json
│   │   ├── tools/
│   │   │   ├── tool_config.json
│   │   │   └── *_tools.py
│   │   ├── ui/
│   │   │   ├── package.json
│   │   │   └── start.sh
│   │   └── services/
│   │       └── worker/
│   │           ├── service_config.json
│   │           └── start.sh
│   └── (other extensions...)
├── hub_ui/
├── .env                            (git-ignored)
└── requirements.txt2. Bootstrap ScriptLocation
luna.sh in repository rootPurpose
Minimal launcher that starts supervisor and monitors its healthHow to Run
For MVP, run manually:
bashcd /opt/luna/luna-repo
./luna.shOr run in background session (screen, tmux, etc). User's choice - no prescribed process manager.Not using systemd because update script stops entire system and we don't want external process manager interfering with shutdown/restart cycle.Responsibilities

Start supervisor process if not running
Health check supervisor every 10 seconds
After 3 consecutive health check failures, kill and restart supervisor
Run in infinite loop
Flow
Loop forever:
  Check if supervisor process exists
    If not running:
      Start supervisor
      Wait 5 seconds
      Continue loop
  
  Health check via GET http://127.0.0.1:9999/health
    If success:
      Reset failure counter to 0
    If failure:
      Increment failure counter
      
      If failure counter >= 3:
        Kill supervisor process (SIGKILL)
        Reset failure counter
        Continue loop (will restart)
  
  Sleep 10 seconds3. SupervisorLocation
supervisor/supervisor.pyPurpose
Master process manager that orchestrates all Luna servicesStartup FlowCheck for pending updates:
If core/update_queue.json exists:
  Copy core/scripts/apply_updates.py to /tmp/luna_apply_updates.py
  Spawn apply_updates as detached background process
  Exit supervisor (code 0)Normal startup (no queue):
Load or initialize master_config.json
Initialize or load state.json
Run config_sync.py
Start core services (Hub UI, Agent API, MCP Server)
Discover enabled extensions
Start extension UIs with port assignment
Start extension services with port assignment
Set LUNA_PORTS environment variable for all services
Begin health monitoring loop
Expose supervisor API on port 9999Initial SetupFirst time running Luna (no master_config.json exists):
Supervisor creates default master_config.json:
  {
    "luna": {
      "version": "{current_date}",
      "timezone": "UTC",
      "default_llm": "gpt-4"
    },
    "extensions": {},
    "tool_configs": {},
    "port_assignments": {
      "extensions": {},
      "services": {}
    }
  }

Scan extensions/ directory for any bundled extensions
For each found:
  Read extension config.json
  Add to master_config.extensions with enabled=true
  
Continue normal startupPort Assignment StrategyFor extension UIs:
Read master_config.port_assignments.extensions
If extension name exists in dictionary:
  Use that port
Else:
  Find next available port starting from 5200
  Add to dictionary
  Save master_configFor extension services:
Read service name from services/{service}/service_config.json
Create key: "{extension_name}.{service_name}"
Read master_config.port_assignments.services
If key exists in dictionary:
  Use that port
Else if service requires_port is true:
  Find next available port starting from 5300
  Add to dictionary with key
  Save master_config
Else:
  Port is null (service doesn't need port)Example port assignments:
json{
  "port_assignments": {
    "extensions": {
      "notes": 5200,
      "todos": 5201,
      "github_sync": 5202
    },
    "services": {
      "github_sync.webhook_receiver": 5300,
      "email_processor.queue_worker": null
    }
  }
}Extension and service names are stable (based on folder names and service_config.json), ensuring ports remain consistent across restarts.Health MonitoringProcess:
Every 30 seconds:
  For each service:
    Poll GET /{healthz_endpoint}
    
    If success:
      status = "running"
      Reset failure counter for this service (in memory)
    
    If failure:
      Increment failure counter for this service (in memory)
      
      If failure counter = 2:
        Stop the process:
          Send SIGTERM
          Wait 5 seconds
          Send SIGKILL if still running
        
        Increment restart attempt counter (in memory)
        
        If restart attempts < 2:
          Start process again
          Reset failure counter
          Update state.json
        Else:
          status = "failed"
          Give up on this service
          Update state.json
          
    Update state.json with current statusCounters tracked in memory only (not persisted):

Health failure count per service
Restart attempt count per service
Manual restart resets counters for that service.Environment VariablesBefore starting each service, supervisor exports:
bashexport LUNA_PORTS='{
  "core": {"hub_ui": 5173, "agent_api": 8080, "mcp_server": 8765},
  "extensions": {"notes": 5200, "todos": 5201},
  "services": {"github_sync.webhook_receiver": 5300}
}'Services can parse this JSON to discover other service ports.Restart HandlerWhen POST /restart is called:
Copy core/scripts/apply_updates.py to /tmp/
Spawn apply_updates as detached process
Shutdown all services gracefully:
  For each service in reverse start order:
    Send SIGTERM
    Wait up to 5 seconds
    Send SIGKILL if still running
Exit supervisor (code 0)Bootstrap will detect supervisor exit and entire system will be down. Apply_updates will restart the system after applying changes.API EndpointsGET /health

Returns: HTTP 200 with {"status": "healthy"}
Used by: Bootstrap for health monitoring
GET /services/status

Returns: Current state.json contents
Used by: Hub UI to display service statuses
GET /ports

Returns: Port mapping dictionary
Format: {"core": {...}, "extensions": {...}, "services": {...}}
Used by: Services that need dynamic port discovery (alternative to env var)
POST /restart

Initiates restart and update flow
Returns: {"status": "restarting"}
Used by: Hub UI when user clicks restart
State FileLocation: supervisor/state.jsonStructure:
json{
  "services": {
    "hub_ui": {
      "pid": 1001,
      "port": 5173,
      "status": "running"
    },
    "agent_api": {
      "pid": 1002,
      "port": 8080,
      "status": "running"
    },
    "notes_ui": {
      "pid": 1004,
      "port": 5200,
      "status": "unhealthy"
    },
    "github_sync.webhook_receiver": {
      "pid": 1005,
      "port": 5300,
      "status": "running"
    }
  }
}Status values:

"running" - Process alive, health checks passing
"unhealthy" - Process alive, health checks failing
"stopped" - No process running
"failed" - Restart attempts exhausted, gave up
Only tracks: pid, port, status (minimal MVP tracking)Not tracked: timestamps, uptime, health check counts (those are in memory)4. Apply Updates ScriptLocation
core/scripts/apply_updates.pyExecution Context

Copied to and run from /tmp/luna_apply_updates.py
Receives repository path as command line argument
Runs with no other Luna processes active (system fully shut down)
Can safely modify any file in repository
Execution FlowPhase 1: Check for Queue
Change directory to repository path (from argument)
Check if core/update_queue.json exists
If not exists:
  Restart bootstrap (exec luna.sh)
  Exit

Read and parse queue:
  operations array
  master_config objectPhase 2: Delete Operations
For each operation where type is "delete":
  Remove extensions/{target}/ directory completelyPhase 3: Install Operations
For each operation where type is "install":
  Parse source string:
  
  If source format is "github:user/repo:path/to/subfolder":
    Parse into: repo = "user/repo", subpath = "path/to/subfolder"
    Clone repository to temporary location
    Copy subpath directory to extensions/{target}/
    Remove temporary clone directory
  
  Else if source format is "github:user/repo":
    Clone repository directly to extensions/{target}/
  
  Else if source format is "upload:filename.zip":
    Unzip /tmp/{filename} to extensions/ directoryPhase 4: Update Operations
For each operation where type is "update":
  Parse source string (same logic as install)
  
  If source is "github:user/repo" (no subpath):
    Change to extensions/{target}/ directory
    Run: git fetch origin
    Run: git reset --hard origin/main
  
  Else (github with subpath or upload):
    Remove extensions/{target}/ directory
    Re-install using install logic from Phase 3Phase 5: Core Update Operations
For each operation where type is "update_core":
  Change to repository root directory
  Run: git fetch origin
  Run: git reset --hard origin/mainPhase 6: Install All Dependencies
Install core dependencies:
  Run: pip install -r requirements.txt --break-system-packages
  If hub_ui/package.json exists:
    Change to hub_ui/ directory
    Run: pnpm install

Install extension dependencies:
  For each directory in extensions/:
    If requirements.txt exists:
      Run: pip install -r requirements.txt --break-system-packages
    
    If ui/package.json exists:
      Change to ui/ directory
      Run: pnpm install
    
    For each service directory in services/:
      If requirements.txt exists:
        Run: pip install -r requirements.txt --break-system-packagesPhase 7: Overwrite Master Config
Write queue.master_config to core/master_config.json
This applies all configuration changesPhase 8: Clear Queue
Delete core/update_queue.jsonPhase 9: Cleanup and Restart System
Delete /tmp/luna_apply_updates.py
Execute: {repository_path}/luna.sh
This restarts bootstrap which starts supervisorInstall Dependencies UtilityAPI Endpoint: POST /api/extensions/install-dependenciesFunctionality: Runs Phase 6 logic (install all dependencies) without requiring full restartUse Case: After manually editing extension files or debugging dependency issues5. Config Sync ScriptLocation
core/scripts/config_sync.pyPurpose
Synchronize user preferences from master_config into extension config files on diskWhen It Runs
Called by supervisor during normal startup (when no update queue exists)ProcessFor each extension in master_config.extensions:
Construct path: extensions/{extension_name}/config.json

If file doesn't exist:
  Skip this extension (was deleted)
  Continue to next

Read extension config from disk
Read master config data for this extension

Generic key matching:
  For each key in extension config:
    If same key exists in master config.config:
      Overwrite extension config value with master value
    Else:
      Keep extension config value (not in master)
  
  Special handling:
    Never overwrite "version" field (extension version is authoritative)
    If extension config has no version field:
      Use current date (MM-DD-YY) as version
    Add "enabled" from master to extension config
    Add "source" from master to extension config

Write modified extension config back to disk

Sync tool configs:
  If tools/tool_config.json exists:
    Read tool config from disk
    For each tool in master_config.tool_configs:
      If tool name matches a tool in this extension:
        Update tool settings with master values
    Write tool config back to diskMissing Version Field HandlingIf extension config.json lacks version field:
Config sync:
  Generate version from current date (MM-DD-YY)
  Add to extension config
  This ensures every extension has a version after syncExampleMaster config contains:
json{
  "extensions": {
    "notes": {
      "enabled": true,
      "source": "github:user/notes",
      "config": {
        "max_notes": 1000,
        "theme": "dark"
      }
    }
  }
}Extension config on disk:
json{
  "version": "10-17-25",
  "max_notes": 100,
  "auto_save": true,
  "theme": "light",
  "required_secrets": ["OPENAI_API_KEY"]
}After config_sync:
json{
  "version": "10-17-25",
  "max_notes": 1000,
  "auto_save": true,
  "theme": "dark",
  "enabled": true,
  "source": "github:user/notes",
  "required_secrets": ["OPENAI_API_KEY"]
}Notice:

version not overwritten (stays 10-17-25)
max_notes overwritten (matched key)
theme overwritten (matched key)
auto_save preserved (not in master)
enabled and source added from master
required_secrets preserved (not in master)
6. Master ConfigLocation
core/master_config.json (git-ignored)Purpose
Single source of truth for all Luna and extension stateStructurejson{
  "luna": {
    "version": "10-17-25",
    "timezone": "America/New_York",
    "default_llm": "gpt-4.1"
  },
  
  "extensions": {
    "automation_memory": {
      "enabled": true,
      "source": "github:luna-team/automation-memory",
      "config": {
        "max_memories": 500,
        "retention_days": 90,
        "auto_cleanup": true
      }
    },
    "notes": {
      "enabled": false,
      "source": "github:user/luna-extensions:embedded/notes",
      "config": {
        "max_notes": 1000,
        "auto_save": true,
        "theme": "dark"
      }
    }
  },
  
  "tool_configs": {
    "AUTOMATION_CREATE_scheduled_task": {
      "enabled_in_mcp": true,
      "passthrough": false
    },
    "NOTES_UPDATE_project_note": {
      "enabled_in_mcp": false,
      "passthrough": false
    }
  },
  
  "port_assignments": {
    "extensions": {
      "notes": 5200,
      "todos": 5201,
      "github_sync": 5202
    },
    "services": {
      "github_sync.webhook_receiver": 5300,
      "email_processor.worker": null
    }
  }
}Field Descriptionsluna section:

version - Core Luna version (MM-DD-YY format)
timezone - Display timezone for UI
default_llm - Default LLM model for agents
extensions section (per extension):

enabled (boolean) - Whether to start on boot
source (string) - Where to get updates, formats:

"github:user/repo" - External repository
"github:user/repo:path/to/subfolder" - Monorepo subfolder
"upload:filename.zip" - Uploaded zip file


config (object) - Extension-specific settings (user preferences)
tool_configs section:

Flat namespace of all tools across all extensions
Each tool has enabled_in_mcp and passthrough booleans
port_assignments section:

extensions - Maps extension names to UI ports
services - Maps "{extension}.{service}" keys to service ports (null if no port)
Ensures stable port assignments across restarts
Note: Version is NOT stored in master_config per extension. Version comes from extension's own config.json and is never overwritten.7. Update QueueLocation
core/update_queue.json (git-ignored)Purpose
Staging area for all pending changes before restartStructurejson{
  "operations": [
    {
      "type": "delete",
      "target": "old_extension"
    },
    {
      "type": "install",
      "source": "github:user/luna-extensions:embedded/notes",
      "target": "notes"
    },
    {
      "type": "update",
      "source": "github:user/github-sync",
      "target": "github_sync"
    },
    {
      "type": "update_core",
      "target_version": "10-20-25"
    }
  ],
  
  "master_config": {
    "luna": {...},
    "extensions": {...},
    "tool_configs": {...},
    "port_assignments": {...}
  }
}Operations Typesdelete:

target - Extension name to remove
install:

source - Where to get extension (github or upload)
target - Extension name (folder name)
update:

source - New source location
target - Extension name to update
update_core:

target_version - Version string (for reference only)
How It's CreatedUser makes changes in Extension Manager UI:

Changes are staged in React state
User clicks "Save to Queue"
Frontend compares original vs current state
Generates operations list (install/update/delete)
Packages entire current state as master_config
Sends to backend: POST /api/queue/save
Backend writes to update_queue.json
How It's ConsumedSupervisor checks for queue on startup:

If exists: trigger update flow
apply_updates executes all operations
Overwrites master_config.json
Deletes queue file
System restarts with changes applied
8. Extension ConfigLocation
extensions/{name}/config.json (per extension)Purpose
Extension's own configuration, maintained by extension developerStructurejson{
  "version": "10-17-25",
  "max_notes": 100,
  "auto_save": true,
  "theme": "light",
  "required_secrets": ["OPENAI_API_KEY", "NOTION_API_KEY"]
}Key Pointsversion field:

Set by extension developer
Uses MM-DD-YY format
Config sync NEVER overwrites this field
Authoritative source for extension version
If missing, config sync generates from current date
Extension-specific settings:

Arbitrary keys and values
Config sync overwrites matching keys from master_config
Non-matching keys are preserved
required_secrets array:

Lists which secrets from .env this extension needs
Used by Key Manager to display requirements
After config_sync:

Additional fields added: enabled, source
These come from master_config but are added to extension config for self-documentation
9. Tool ConfigLocation
extensions/{name}/tools/tool_config.json (per extension)Purpose
Configuration for each tool in the extensionStructurejson{
  "NOTES_CREATE_note": {
    "enabled_in_mcp": true,
    "passthrough": false
  },
  "NOTES_UPDATE_note": {
    "enabled_in_mcp": true,
    "passthrough": false
  },
  "NOTES_DELETE_note": {
    "enabled_in_mcp": false,
    "passthrough": false
  }
}Fields (per tool)enabled_in_mcp (boolean):

Whether this tool is exposed to MCP server
If false, tool only available to internal Luna agents
passthrough (boolean):

For passthrough_agent only
If true, agent can use tool without validating input/output
If false, agent validates tool execution
Config SyncMaster config has flat tool namespace:
json{
  "tool_configs": {
    "NOTES_CREATE_note": {"enabled_in_mcp": false, "passthrough": false}
  }
}Config sync updates extension's tool_config.json with matching tools from master.10. Service ConfigLocation
extensions/{name}/services/{service}/service_config.json (per service)Purpose
Metadata about a background serviceStructurejson{
  "name": "webhook_receiver",
  "requires_port": true,
  "health_check": "/healthz",
  "restart_on_failure": true
}Fieldsname (string, required):

Unique identifier for this service
Used for port assignment key: "{extension}.{service_name}"
Must be stable across updates
requires_port (boolean, default false):

Whether service needs a network port
If true, supervisor assigns port from 5300+ range
If false, port is null
health_check (string, nullable):

Endpoint path to poll if requires_port is true
Example: "/healthz"
If null, no health checking for this service
restart_on_failure (boolean, default true):

Whether supervisor should auto-restart on health check failure
If false, service stays stopped after failure
11. Extension Manager UILocation
React component in Hub UIPurpose
User interface for managing extensions, tools, and secretsState ManagementThree-state system:
javascriptoriginalState  // Loaded from server on page open
currentState   // User's working state with unsaved changes
queuedState    // What's saved in update_queue.jsonAll changes update currentState locally until user clicks "Save to Queue".Main View - Extension CardsLayout: Grid of cards, each representing one extensionCard Contents:

Extension name
Version (MM-DD-YY format)
Enabled/disabled toggle
Health status indicator (colored dot)
Tool count
Service count (if any)
Action buttons: Details, Delete
Card Visual:
┌──────────────────────────────────┐
│ 📝 Notes       v10-17-25    [◉] │
│ ● Running                        │
│ 3 tools                          │
│ [Details]  [Delete]              │
└──────────────────────────────────┘Extension Detail PageNavigation: Click extension card to open detail pageHeader: Extension name, version, back buttonTabs:Tools Tab:

List all tools from this extension
Each tool shows:

Tool name
Description (extracted from docstring)
Two checkboxes:

 Enabled in MCP
 Passthrough mode




Checkbox changes update currentState immediately
No validation - just state updates
Services Tab:

List all services for this extension
Each service shows:

Service name
Status (running/unhealthy/stopped/failed)
Port number (if assigned)
Manual control buttons: Start, Stop, Restart


Buttons call supervisor API directly (no queue needed)
About Tab:

Extension readme content
Version information
Required secrets list
Source repository link
User ActionsUpload Extension:
User selects file via file picker
  ↓
Frontend uploads file
  POST /api/extensions/upload
  Multipart form data
  ↓
Backend saves to /tmp/{unique_filename}.zip
Returns: {temp_filename: "..."}
  ↓
Frontend extracts extension name from original filename
  ↓
Check if originalState has this extension name:
  If yes: This is an UPDATE
  If no: This is an INSTALL
  ↓
Add to currentState.extensions:
  {
    enabled: true,
    source: "upload:{temp_filename}.zip",
    config: existing_config or {}
  }
  ↓
UI shows change in pending changes listToggle Extension Enabled:
User clicks toggle on extension card
  ↓
Update currentState.extensions[name].enabled
  ↓
UI updates to show change in pending listChange Tool Config:
User checks/unchecks tool checkbox in detail page
  ↓
Update currentState.tool_configs[tool_name]
  ↓
UI updatesSave to Queue:
User clicks "Save to Queue" button
  ↓
Compare originalState vs currentState
  ↓
Generate operations array:
  For each extension in originalState not in currentState:
    Add {type: "delete", target: name}
  
  For each extension in currentState:
    If not in originalState:
      Add {type: "install", source: ..., target: name}
    Else if source changed:
      Add {type: "update", source: ..., target: name}
  ↓
Package queue:
  {
    operations: [...],
    master_config: currentState
  }
  ↓
POST /api/queue/save
  ↓
Backend writes to update_queue.json
  ↓
Set queuedState = queue
  ↓
UI shows "Queue saved" messageRevert to Original:
User clicks "Revert All Changes"
  ↓
Set currentState = originalState
  ↓
All pending changes disappearDelete Queue:
User clicks "Delete Queue"
  ↓
DELETE /api/queue/current
  ↓
Backend deletes update_queue.json
  ↓
Set queuedState = null
  ↓
UI updatesRestart System:
User clicks "Restart & Apply Updates"
  ↓
POST /api/system/restart
  ↓
Backend triggers supervisor restart flow
  ↓
Frontend shows "System restarting..." modal
  ↓
Frontend polls GET /health every 2 seconds
  ↓
When health returns 200:
  Reload page
  Load new originalState
  Queue is now emptyInstall Dependencies (manual utility):
User clicks "Install Dependencies" button
  ↓
POST /api/extensions/install-dependencies
  ↓
Backend runs dependency installation (Phase 6 logic)
  ↓
No restart needed
  ↓
Shows success/failure toastTabsExtensions Tab: Main view with extension cardsQueue Tab:

Shows all pending operations
Shows count of pending changes
Buttons:

"Save to Queue" (enabled if currentState != originalState)
"Revert to Original" (enabled if currentState != originalState)
"Delete Queue" (enabled if queuedState exists)
"Restart & Apply Updates" (enabled if queuedState exists)


Store Tab: Browse and install from extension storeSecrets Tab: Key Manager interface12. Key ManagerLocation
Tab within Extension Manager UIPurpose
Manage secrets in .env file with immediate hot reload (no restart required)FeaturesScan Required Secrets:
On page load:
  For each extension in extensions/:
    Read extensions/{name}/config.json
    Extract required_secrets array
  
  Aggregate all unique secret names
  
  Read .env file
  
  For each required secret:
    Check if exists in .env
    Display status: set or not setUpload .env File:
User selects .env file
  ↓
POST /api/keys/upload-env
Multipart form data
  ↓
Backend:
  Parse uploaded .env file
  Load existing .env file
  Merge: uploaded values override existing
  Write merged result atomically to .env
  Call load_dotenv(override=True) to hot reload
  ↓
Return: {updated_count: N}
  ↓
Frontend shows success messageAdd/Edit Secret:
User enters key and value in form
  ↓
POST /api/keys/set
Body: {key: "SECRET_NAME", value: "secret_value"}
  ↓
Backend:
  Load .env file
  Update or add key
  Write atomically
  Hot reload with load_dotenv
  ↓
Return: {status: "updated"}
  ↓
Frontend shows success
  ↓
No restart needed - services read from environment on next accessDelete Secret:
User clicks delete button
  ↓
Confirm dialog
  ↓
POST /api/keys/delete
Body: {key: "SECRET_NAME"}
  ↓
Backend:
  Load .env
  Remove key
  Write atomically
  Hot reload
  ↓
Frontend updates displayUI Layout━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Key Manager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Upload .env File
[Choose File] [Upload & Merge]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Required by Extensions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

automation_memory
  ✅ OPENAI_API_KEY = sk-...abc  [Edit]

github_sync
  ✅ GITHUB_TOKEN = ghp_...xyz  [Edit]
  ❌ GITHUB_WEBHOOK_SECRET (not set)  [Add]

notes
  ✅ NOTION_API_KEY = secret_...  [Edit]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Custom Secrets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ MY_CUSTOM_KEY = abc...123  [Edit] [Delete]

[+ Add Custom Secret]Why No Restart NeededServices use environment variables via standard methods that read from current environment. After Key Manager updates .env and hot reloads, the process environment is updated. Next time service accesses a secret, it gets the new value.Caveat: If service caches secrets at startup, it needs restart. But most services should read on-demand for this to work.13. Extension StorePurpose
Browse and install extensions from central repositoryArchitectureCentral Repository: GitHub monorepo at luna-extensionsStructure:
luna-extensions/
├── registry.json           Master catalog
├── embedded/              Small extensions (code included)
│   ├── notes/
│   │   ├── config.json
│   │   ├── tools/
│   │   └── readme.md
│   ├── todos/
│   ├── calendar/
│   ├── clipboard/
│   └── weather/
└── external/              Large extensions (metadata only)
    ├── github_sync.json
    ├── slack.json
    └── jira.jsonRegistry FileLocation: luna-extensions/registry.jsonStructure:
json{
  "version": "10-17-25",
  "last_updated": "2025-10-17T12:00:00Z",
  
  "extensions": [
    {
      "id": "notes",
      "name": "Notes",
      "type": "embedded",
      "path": "embedded/notes",
      "version": "10-17-25",
      "description": "Simple note-taking with tags and search",
      "author": "Luna Team",
      "category": "productivity",
      "has_ui": false,
      "tool_count": 3,
      "required_secrets": ["OPENAI_API_KEY"],
      "tags": ["notes", "productivity", "text"]
    },
    {
      "id": "github_sync",
      "name": "GitHub Sync",
      "type": "external",
      "source": "github:luna-extensions-official/github-sync",
      "version": "10-15-25",
      "description": "Sync GitHub issues, PRs, and repositories",
      "author": "Luna Team",
      "category": "development",
      "has_ui": true,
      "tool_count": 12,
      "service_count": 1,
      "required_secrets": ["GITHUB_TOKEN", "GITHUB_WEBHOOK_SECRET"],
      "tags": ["github", "development", "sync"],
      "preview_url": "https://github.com/luna-extensions-official/github-sync"
    }
  ],
  
  "categories": [
    {"id": "productivity", "name": "Productivity"},
    {"id": "development", "name": "Development"},
    {"id": "communication", "name": "Communication"},
    {"id": "automation", "name": "Automation"}
  ]
}Store UILocation: Store tab in Extension ManagerFeatures:

Fetch registry.json on page load
Display extensions in grid or list
Search by name or tags
Filter by category
Filter by has_ui / no_ui
Show extension details on click
Install button per extension
Extension Card in Store:
┌──────────────────────────────────┐
│ Notes                 v10-17-25  │
│ Simple note-taking with tags     │
│                                  │
│ 3 tools • No UI • Productivity   │
│ Requires: OPENAI_API_KEY         │
│                                  │
│ [Install]                        │
└──────────────────────────────────┘Installation FlowFor embedded extension:
User clicks "Install Notes"
  ↓
Registry shows:
  type: "embedded"
  path: "embedded/notes"
  ↓
Generate install operation:
  {
    type: "install",
    source: "github:user/luna-extensions:embedded/notes",
    target: "notes"
  }
  ↓
Add to currentState
  ↓
User saves to queue
  ↓
On restart, apply_updates:
  Clone luna-extensions to /tmp/luna-ext-temp/
  Copy embedded/notes/ to extensions/notes/
  Remove temp directoryFor external extension:
User clicks "Install GitHub Sync"
  ↓
Registry shows:
  type: "external"
  source: "github:luna-extensions-official/github-sync"
  ↓
Generate install operation:
  {
    type: "install",
    source: "github:luna-extensions-official/github-sync",
    target: "github_sync"
  }
  ↓
Add to currentState
  ↓
User saves to queue
  ↓
On restart, apply_updates:
  Clone github-sync directly to extensions/github_sync/BenefitsSingle monorepo for small extensions (easy maintenance)Separate repositories for large/complex extensions (independence)Single registry file (one source of truth)Version control via git (automatic versioning)Can move embedded to external as extension growsStandard industry pattern (VS Code, Kubernetes, etc.)14. Complete FlowsNormal Startup (No Queue)Bootstrap starts
  ↓
Bootstrap starts Supervisor process
  ↓
Supervisor checks for core/update_queue.json
  File not found
  ↓
Load or create core/master_config.json
  If doesn't exist: create default with empty extensions
  ↓
Initialize or load supervisor/state.json
  (includes port_assignments for reuse)
  ↓
Run core/scripts/config_sync.py
  Sync master config to all extension configs
  Never overwrite version field
  If extension has no version: generate from current date
  Add enabled and source fields
  ↓
Start core services:
  Hub UI on port 5173
  Agent API on port 8080
  MCP Server on port 8765
  ↓
Discover enabled extensions from master_config
  ↓
For each enabled extension with ui/ folder:
  Check port_assignments.extensions[name]
    If exists: use that port
    Else: assign next from 5200+, save to master_config
  Set LUNA_PORTS environment variable
  Run extensions/{name}/ui/start.sh {port}
  Record pid, port, status in state.json
  ↓
For each extension with services/ folder:
  For each service subdirectory:
    Read service_config.json
    Get service name
    Create key: "{extension}.{service_name}"
    
    If requires_port is true:
      Check port_assignments.services[key]
        If exists: use that port
        Else: assign next from 5300+, save to master_config
      Set LUNA_PORTS environment variable
      Run start.sh {port}
    Else:
      No port needed
      Run start.sh with no arguments
    
    Record pid, port, status in state.json
  ↓
Begin health monitoring loop:
  Every 30 seconds:
    Poll each service /healthz endpoint
    Update status based on response
    Handle failures per health check logic
  ↓
Expose supervisor API on port 9999:
  GET /health
  GET /services/status
  GET /ports
  POST /restart
  ↓
Write final state.json
  ↓
System fully operationalStartup with Queued UpdatesBootstrap starts Supervisor
  ↓
Supervisor checks for core/update_queue.json
  File found!
  ↓
Copy core/scripts/apply_updates.py to /tmp/luna_apply_updates.py
  ↓
Spawn apply_updates as detached background process:
  Command: python /tmp/luna_apply_updates.py /opt/luna/luna-repo
  Detached: no parent process
  ↓
Supervisor exits with code 0
  ↓
Bootstrap detects supervisor exit
  ↓
Bootstrap also exits
  ↓
Entire Luna system now shut down
  ↓
apply_updates.py runs standalone:
  ↓
  Phase 1: Check queue
    Read core/update_queue.json
    Parse operations and master_config
  ↓
  Phase 2: Delete operations
    For each delete: rm -rf extensions/{target}/
  ↓
  Phase 3: Install operations
    For each install:
      Parse source format
      If github with subpath: clone to temp, copy subfolder
      If github without subpath: clone directly
      If upload: unzip to extensions/
  ↓
  Phase 4: Update operations
    For each update:
      If github without subpath: git reset --hard origin/main
      If other: delete and reinstall
  ↓
  Phase 5: Core update (if present)
    git reset --hard origin/main in repo root
  ↓
  Phase 6: Install all dependencies
    Core: pip install -r requirements.txt
    Core: pnpm install in hub_ui/
    Extensions: pip install for each requirements.txt
    Extensions: pnpm install for each ui/package.json
    Services: pip install for each service requirements.txt
  ↓
  Phase 7: Overwrite master config
    Write queue.master_config to core/master_config.json
    This includes updated port_assignments
  ↓
  Phase 8: Clear queue
    Delete core/update_queue.json
  ↓
  Phase 9: Restart system
    Delete /tmp/luna_apply_updates.py
    Execute: /opt/luna/luna-repo/luna.sh
  ↓
Bootstrap starts fresh
  ↓
Bootstrap starts Supervisor
  ↓
Supervisor checks queue → not found (was cleared)
  ↓
Normal startup continues with updated systemExtension Upload and InstallUser opens Extension Manager
  ↓
User clicks "Upload Extension"
  ↓
File picker opens
  ↓
User selects todos.zip
  ↓
Frontend uploads file:
  POST /api/extensions/upload
  Multipart form: file=todos.zip
  ↓
Backend:
  Generate unique filename: todos_1697456789.zip
  Save to /tmp/{unique_filename}
  Return: {temp_filename: "todos_1697456789.zip"}
  ↓
Frontend:
  Extract extension name from original filename: "todos"
  Check if originalState.extensions.todos exists:
    Not found → This is INSTALL
  ↓
  Add to currentState.extensions.todos:
    {
      enabled: true,
      source: "upload:todos_1697456789.zip",
      config: {}
    }
  ↓
UI updates to show "Install todos" in pending changes
  ↓
User reviews change
  ↓
User clicks "Save to Queue"
  ↓
Frontend generates operations:
  [{
    type: "install",
    source: "upload:todos_1697456789.zip",
    target: "todos"
  }]
  ↓
Frontend packages queue:
  {
    operations: [...],
    master_config: currentState (entire state)
  }
  ↓
POST /api/queue/save with queue object
  ↓
Backend writes to core/update_queue.json
  ↓
Frontend sets queuedState
  ↓
UI shows "Queue saved (1 update)" message
  ↓
User clicks "Restart & Apply Updates"
  ↓
POST /api/system/restart
  ↓
Supervisor restart flow begins
  ↓
Frontend shows "Restarting..." modal
  ↓
apply_updates.py extracts /tmp/todos_1697456789.zip to extensions/todos/
  ↓
Installs dependencies
  ↓
Overwrites master_config (now includes todos)
  ↓
System restarts
  ↓
Frontend detects system is back (health check passes)
  ↓
Reload page
  ↓
Load new originalState (includes todos)
  ↓
Todos extension visible in extension listInstall from Extension StoreUser opens Store tab
  ↓
Frontend fetches registry:
  GET https://raw.githubusercontent.com/user/luna-extensions/main/registry.json
  ↓
Parse registry, display extensions
  ↓
User clicks "Install Notes"
  ↓
Frontend reads registry entry:
  {
    id: "notes",
    type: "embedded",
    path: "embedded/notes"
  }
  ↓
Generate install operation:
  {
    type: "install",
    source: "github:user/luna-extensions:embedded/notes",
    target: "notes"
  }
  ↓
Add to currentState.extensions.notes:
  {
    enabled: true,
    source: "github:user/luna-extensions:embedded/notes",
    config: {}
  }
  ↓
UI shows "Install notes" in pending changes
  ↓
User clicks "Save to Queue"
  ↓
Queue saved to update_queue.json
  ↓
User clicks "Restart & Apply Updates"
  ↓
apply_updates.py:
  Clone luna-extensions repo to /tmp/
  Copy embedded/notes/ to extensions/notes/
  Remove temp directory
  Install dependencies
  ↓
Next startup includes notes extensionInter-Service CommunicationExtension service needs to call Agent API
  ↓
Service reads LUNA_PORTS environment variable
  ↓
Get Agent API port from parsed JSON
  Returns: 8080
  ↓
Construct URL: http://127.0.0.1:8080/v1/chat/completions
  ↓
Make request
  ↓
Process responseAlternative method:
Service queries supervisor directly:
  GET http://127.0.0.1:9999/ports
  ↓
Returns current port mapping
  ↓
Service caches or uses immediately15. Port AssignmentsCore Services (Fixed)
Hub UI: 127.0.0.1:5173
Agent API: 127.0.0.1:8080
MCP Server: 127.0.0.1:8765
Supervisor API: 127.0.0.1:9999
These ports never change.Extension UIs (Dynamic, Persistent)
Range: 127.0.0.1:5200 through 127.0.0.1:5299
Assignment: Sequential starting from 5200
Persistence: Stored in master_config.port_assignments.extensions
Stability: Extension name is key, port reused on restart
Example:
json{
  "port_assignments": {
    "extensions": {
      "notes": 5200,
      "todos": 5201,
      "github_sync": 5202
    }
  }
}If notes extension exists, it always gets port 5200 even across restarts.Extension Services (Dynamic, Persistent)
Range: 127.0.0.1:5300 through 127.0.0.1:5399
Assignment: Sequential starting from 5300
Persistence: Stored in master_config.port_assignments.services
Key format: "{extension_name}.{service_name}"
Service name from: service_config.json name field
Example:
json{
  "port_assignments": {
    "services": {
      "github_sync.webhook_receiver": 5300,
      "email_processor.queue_worker": null
    }
  }
}Services with requires_port: false have null port.Access MethodsDirect by port: Users access services directly at their ports (no reverse proxy in MVP)Environment variable: Services read LUNA_PORTS for inter-service communicationAPI query: Services can GET supervisor /ports endpoint for dynamic discovery16. Health Check and Restart LogicHealth Check ProcessSupervisor runs health check loop:
  Every 30 seconds:
    For each service with health_check endpoint:
      Make request: GET http://127.0.0.1:{port}{health_check}
      
      If response is 200:
        status = "running"
        Reset failure counter for this service
        Update state.json
      
      If response is not 200 or timeout:
        Increment failure counter in memory
        
        If failure counter = 2:
          Process has failed twice
          Stop the process:
            Send SIGTERM to pid
            Wait up to 5 seconds
            If still running: send SIGKILL
          
          Increment restart attempt counter in memory
          
          If restart attempt counter < 2:
            Start process again using original command
            Reset failure counter
            Update state.json with new pid
          
          Else:
            Restart attempts exhausted
            status = "failed"
            Update state.json
            Stop trying to restartCountersTracked in memory only (not persisted to state.json):

Health failure count per service (resets on success)
Restart attempt count per service (resets on manual restart)
Why memory only: These are runtime tracking for decision making. On supervisor restart, all services start fresh with counters at zero.Manual RestartWhen user clicks restart button in Services tab:
Frontend calls: POST /api/services/{service_name}/restart
  ↓
Supervisor:
  Stop service (SIGTERM, wait, SIGKILL)
  Reset failure counter to 0
  Reset restart attempt counter to 0
  Start service again
  Update state.jsonManual restart gives service a fresh start regardless of previous failures.Status Values
"running" - Process exists, health checks passing
"unhealthy" - Process exists, health checks failing (1 failure)
"stopped" - No process running
"failed" - Restart attempts exhausted (2+ failed restarts), gave up