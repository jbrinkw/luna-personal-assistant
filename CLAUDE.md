Here is a condensed version of the Luna Project Specification, focusing on technical details, schemas, and logic.

### **1. Overview & Vision**

Luna is a personal AI assistant platform serving as a unified hub for AI tools, extensions, and infrastructure services.

  * **Core Features:** Extension management (local/GitHub), Python tool ecosystem (auto-discovery, MCP), agent system (ReAct, Passthrough) with OpenAI-compatible API, Docker-based external services, and a unified React UI.
  * **System Features:** One-line install, auto-discovery, hot reload, health monitoring, and persistent state.
  * **Technology Stack:**
      * **Backend:** Python (FastAPI)
      * **Frontend:** React + Vite
      * **Database:** PostgreSQL (Store: UTC, Display: America/New\_York)
      * **Containerization:** Docker
      * **Process Management:** Custom supervisor (no systemd)
      * **Agent Framework:** LangChain (ReAct)
      * **MCP Integration:** Server-Sent Events (SSE)

### **2. Project Directory Structure**

```
/opt/luna/
├── luna.sh                     # Bootstrap script
├── luna-repo/                  # Main repository (git-tracked)
│   ├── core/
│   │   ├── agents/
│   │   │   ├── simple_agent/
│   │   │   └── passthrough_agent/
│   │   ├── utils/
│   │   │   ├── agent_api.py      # OpenAI-compatible API
│   │   │   ├── mcp_server.py     # MCP SSE server
│   │   │   ├── service_manager.py
│   │   │   └── ...
│   │   ├── scripts/
│   │   │   └── apply_updates.py
│   │   └── master_config.json    # Source of truth
│   ├── supervisor/
│   │   ├── supervisor.py       # Main process manager
│   │   └── state.json          # Runtime state (ephemeral)
│   ├── extensions/
│   │   ├── [extension_name]/
│   │   │   ├── config.json
│   │   │   ├── requirements.txt
│   │   │   ├── tools/
│   │   │   │   ├── tool_config.json
│   │   │   │   └── *_tools.py
│   │   │   ├── ui/               # Optional
│   │   │   │   ├── start.sh
│   │   │   │   └── ...
│   │   │   └── services/         # Optional
│   │   │       └── [service_name]/
│   │   │           ├── start.sh
│   │   │           └── service.json
│   ├── external_services/        # Infrastructure
│   │   ├── postgres/
│   │   │   ├── service.json
│   │   │   ├── config.json       # User config (git-ignored)
│   │   │   └── data/             # Volume (git-ignored)
│   │   └── redis/
│   ├── hub_ui/                   # Main frontend
│   ├── .env                      # Secrets (git-ignored)
│   └── requirements.txt
└── .luna/                        # Logs (git-ignored)
    ├── external_services.json    # Installed service registry
    ├── external_service_routes.json
    └── logs/
```

**Git Ignore Rules:** `.env`, `supervisor/state.json`, `.luna/`, `extensions/*/config.json`, `extensions/*/data/`, `external_services/*/config.json`, `external_services/*/data/`, `__pycache__/`, `node_modules/`, `dist/`, `*.log`.

### **3. Core Architecture**

**3.1. Bootstrap (`/opt/luna/luna.sh`)**
Simple health monitor (outside git repo).

  * **Logic:** `while true`:
    1.  Check if `supervisor.py` process exists. If not, start it.
    2.  `curl` supervisor's `/health` (port 9999).
    3.  If health check fails 3 consecutive times, `pkill` and restart supervisor.
    4.  Sleep 10 seconds.
  * **Script:**
    ```bash
    #!/bin/bash
    LUNA_ROOT="/opt/luna/luna-repo"
    SUPERVISOR_SCRIPT="$LUNA_ROOT/supervisor/supervisor.py"
    SUPERVISOR_PORT=9999
    CHECK_INTERVAL=10
    MAX_FAILS=3
    FAIL_COUNT=0

    while true; do
        if ! pgrep -f "supervisor.py" > /dev/null; then
            echo "[$(date)] Supervisor not running, starting..."
            python3 $SUPERVISOR_SCRIPT &
            sleep 5
            continue
        fi
        
        if curl -sf http://127.0.0.1:$SUPERVISOR_PORT/health > /dev/null 2>&1; then
            FAIL_COUNT=0
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
            if [ $FAIL_COUNT -ge $MAX_FAILS ]; then
                echo "[$(date)] Supervisor unhealthy, restarting..."
                pkill -f supervisor.py
                sleep 2
                FAIL_COUNT=0
            fi
        fi
        sleep $CHECK_INTERVAL
    done
    ```

**3.2. Supervisor (`supervisor/supervisor.py`)**
Master process manager (git-tracked).

  * **On Startup:**
    1.  Check for `core/update_queue.json`.
    2.  **If queue exists:** Copy `apply_updates.py` to `/tmp/`, spawn it detached, and `exit(0)`.
    3.  **If no queue:** Create `master_config.json` (if missing), run Config Sync, start core services (Hub UI, Agent API, MCP Server), discover/start enabled extensions (UIs, services) and external services.
    4.  Begin health monitoring loop (30s) and expose supervisor API (port 9999).
  * **During Operation:**
    1.  Poll `/healthz` endpoints every 30s.
    2.  Track failures; auto-restart (2 failures -\> stop -\> restart; max 2 restarts).
    3.  Maintain `state.json` (PIDs, ports, status).
    4.  Export `LUNA_PORTS` env var for all services.
  * **On Restart Request:**
    1.  Copy `apply_updates.py` to `/tmp/`, spawn it detached.
    2.  Gracefully shutdown all services (SIGTERM -\> 5s wait -\> SIGKILL).
    3.  Exit cleanly (bootstrap will restart it).

**3.3. Apply Updates (`core/scripts/apply_updates.py`)**
Standalone script (run from `/tmp/`) that applies queued changes during shutdown.

  * **Responsibilities:**
    1.  Read `core/update_queue.json`.
    2.  Apply changes (install/uninstall extensions, deps, enable/disable, update configs, install/uninstall external services).
    3.  Write all changes to `master_config.json`.
    4.  Delete `update_queue.json`.
    5.  Signal bootstrap to restart supervisor.
  * **Update Queue Format (`core/update_queue.json`):**
    ```json
    {
      "timestamp": "2025-10-20T12:00:00Z",
      "changes": [
        { "type": "install_extension", "source": "...", "name": "notes" },
        { "type": "enable_extension", "name": "notes" },
        { "type": "install_dependencies", "extension": "notes", "python": true },
        { "type": "update_master_config", "path": "extensions.notes.enabled", "value": true }
      ]
    }
    ```

**3.4. Config Sync**
On supervisor startup, merges `master_config.json` into individual extension `config.json` files.

  * **Rules:**
    1.  **NEVER** overwrite `version` field.
    2.  Only update keys that exist in `master_config`.
    3.  If extension `config.json` has no `version`, generate one (MM-DD-YY).
    4.  Syncs `master_config.tool_configs` to extension `tool_config.json` files.

### **4. Extension System**

**4.1. Extension Structure**

```
extensions/my_extension/
├── config.json         # Manifest
├── requirements.txt
├── tools/
│   ├── tool_config.json
│   └── my_extension_tools.py
├── ui/                 # Optional
│   ├── start.sh
│   └── ...
└── services/           # Optional
    └── worker/
        ├── start.sh
        └── service.json
```

**4.2. Extension Config (`config.json`)**
Manifest for metadata and requirements.

  * **Schema:**
    ```json
    {
      "name": "my_extension",
      "display_name": "My Extension",
      "version": "10-20-25",
      "author": "Your Name",
      "description": "What this extension does",
      "required_secrets": ["API_KEY"],
      "auto_update": false,
      "enabled": true,   /* Added by system */
      "source": "local"  /* Added by system */
    }
    ```
  * **Version:** Must be **MM-DD-YY**. Set by developer, **NEVER** overwritten by sync. Auto-generated if missing.

**4.3. Tool System**

  * **Naming Convention:** `DOMAIN_{GET|UPDATE|ACTION}_VerbNoun` (e.g., `NOTES_CREATE_note`).
  * **Tool File Format (`*_tools.py`):**
    ```python
    from pydantic import BaseModel, Field
    from typing import Tuple

    # System prompt for this domain
    SYSTEM_PROMPT = "The user has access to tools for managing their notes."

    # Pydantic model for input validation
    class NOTES_CREATE_NoteArgs(BaseModel):
        title: str = Field(..., description="Note title")
        content: str = Field(..., description="Note content")

    # Tool function
    def NOTES_CREATE_note(title: str, content: str) -> Tuple[bool, str]:
        """Create a new note with title and content.
        
        Example Prompt: create a note titled "Meeting Notes"
        Example Response: {"success": true, "note_id": "abc123"}
        Example Args: {"title": "string", "content": "string"}
        Notes: Tags are optional.
        """
        try:
            args = NOTES_CREATE_NoteArgs(title=title, content=content)
            # Business logic here
            note_id = "abc123"
            return (True, f'{{"success": true, "note_id": "{note_id}"}}')
        except Exception as e:
            return (False, f'{{"error": "{str(e)}"}}')

    # Export tools
    TOOLS = [NOTES_CREATE_note]
    ```
  * **Docstring:** Must include `Example Prompt`, `Example Response`, `Example Args`, and optional `Notes`.
  * **Return Format:** `Tuple[bool, str]` (success boolean, JSON string response).
  * **Tool Config (`tool_config.json`):**
    ```json
    {
      "NOTES_CREATE_note": {
        "enabled_in_mcp": true,  /* Expose to ChatGPT/Claude */
        "passthrough": false     /* For passthrough_agent */
      }
    }
    ```

**4.4. Extension UI**

  * **`start.sh` Contract:**
    1.  Receives port as `$1`.
    2.  Must bind to `127.0.0.1:$1`.
    3.  Must expose a `GET /healthz` endpoint (returns 200).
    4.  Must stay running in the foreground.
  * **Example `start.sh` (Vite):**
    ```bash
    #!/bin/bash
    PORT=$1
    pnpm vite --port $PORT --host 127.0.0.1
    ```

**4.5. Extension Services (Background Processes)**

  * **Structure:** `extensions/{name}/services/{service_name}/`
  * **`service.json` Schema:**
    ```json
    {
      "name": "worker",
      "requires_port": false,
      "health_check": null, /* e.g., "/healthz" if requires_port is true */
      "restart_on_failure": true
    }
    ```
  * **`start.sh` Contract:** Receives port as `$1` *only if* `requires_port` is true.

### **5. External Services**

Docker-based infrastructure (Postgres, Redis) managed by Luna.

  * **Structure:** `external_services/{name}/` contains `service.json`, `config.json` (user-config, git-ignored), and `data/` (volume, git-ignored).
  * **`service.json` (Single Definition File):** Contains all metadata, config form, and commands.
      * `name`, `display_name`, `description`, `category`, `version`
      * `config_form`: JSON schema for the installation UI (fields: `name`, `label`, `type`, `default`, `required`, `help`).
      * `commands`: Shell commands for `install`, `uninstall`, `start`, `stop`, `restart`, `health_check`. Commands use `{{variable}}` templates (e.g., `docker run -p {{port}}:5432 ...`).
      * `health_check_expected`: Expected string output from `health_check` (e.g., "Up" or "PONG").
      * `install_timeout`: Seconds to wait (e.g., 120).
      * `provides_vars`: List of env var names this service auto-generates (e.g., `DATABASE_URL`).
      * `post_install_env`: Optional mapping of env var names to templated values (supports `{{field}}` tokens). If omitted, raw config values are used when writing `.env`.
      * `ui`: Optional metadata to expose a proxied web UI for the service.
          * `base_path`: Root segment for generated paths (defaults to `ext_service`).
          * `slug`: Override for the path slug (defaults to the service name).
          * `port` **or** `port_field`: Either a literal host port or the name of a saved config field that stores it.
          * `scheme`: Upstream scheme (`http` default).
          * `strip_prefix`: Strip the generated prefix before proxying (defaults to `true`).
          * `enforce_trailing_slash`: Issue a 308 redirect to add `/` (defaults to `true`).
          * `open_mode`: Hint for Hub UI buttons (`iframe` | `new_tab`, defaults to `iframe`). 
  * **Installation Flow:**
    1.  UI POSTs `/api/external-services/{name}/install` with user `config` object.
    2.  Backend validates config, saves to `config.json`.
    3.  Backend executes `install` command (with variables replaced).
    4.  Backend polls `health_check` command until `health_check_expected` is met or `install_timeout`.
    5.  On success: Renders `post_install_env` templates (or uses raw config values) for each `provides_vars` entry and appends them to `.env`.
    6.  On failure: Executes `uninstall` command, deletes `config.json`.
  * **Uninstall Flow:**
    1.  POST `/api/external-services/{name}/uninstall`.
    2.  Backend executes `uninstall` command, deletes `config.json` and `data/`, removes env vars.
  * **Upload:**
    1.  POST `/api/external-services/upload` with a full `service_definition` JSON.
    2.  Backend validates (checks for `name`, `commands.install`, `commands.health_check`, etc.).
    3.  Creates `external_services/{name}/` and saves `service.json`.
  * **Example `service.json` (Postgres snippet):**
    ```json
    {
      "name": "postgres",
      "display_name": "PostgreSQL",
      "version": "16-alpine",
      "config_form": {
        "fields": [
          { "name": "database", "label": "Database Name", "type": "text", "default": "luna" },
          { "name": "user", "label": "Username", "type": "text", "default": "luna_user" },
          { "name": "password", "label": "Password", "type": "password", "required": true },
          { "name": "port", "label": "Port", "type": "number", "default": 5432 }
        ]
      },
      "commands": {
        "install": "mkdir -p ... && docker run -d --name luna_postgres --restart unless-stopped -p {{port}}:5432 -e POSTGRES_DB={{database}} -e POSTGRES_USER={{user}} -e POSTGRES_PASSWORD={{password}} -v $(pwd)/external_services/postgres/data:/var/lib/postgresql/data postgres:16-alpine ...",
        "uninstall": "docker stop luna_postgres && docker rm luna_postgres",
        "start": "docker start luna_postgres",
        "stop": "docker stop luna_postgres",
        "health_check": "docker ps --filter name=luna_postgres --format '{{.Status}}'"
      },
      "health_check_expected": "Up",
      "provides_vars": ["DATABASE_URL", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"],
      "post_install_env": {
        "DATABASE_URL": "postgresql://{{ user }}:{{ password }}@127.0.0.1:{{ port }}/{{ database }}",
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "{{ port }}",
        "POSTGRES_DB": "{{ database }}",
        "POSTGRES_USER": "{{ user }}",
        "POSTGRES_PASSWORD": "{{ password }}"
      }
    }
    ```
  * **Example `ui` block (Grocy snippet):**
    ```json
    {
      "ui": {
        "base_path": "ext_service",
        "slug": "grocy",
        "port_field": "port",
        "strip_prefix": true,
        "enforce_trailing_slash": true,
        "open_mode": "iframe"
      }
    }
    ```
  * **Routing Metadata:** Derived UI routes live in `.luna/external_service_routes.json` and are merged into the generated Caddyfile automatically.

### **6. Core Services**

  * **Hub UI:** (React + Vite)
      * **Location:** `luna-repo/hub_ui/`
      * **Port:** `5173` (fixed)
      * **Features:** Manages extensions, external services, `.env` keys. Aggregates extension UIs in `iframes` (`/ext/{extension_name}`).
      * **Health:** `GET /healthz`
  * **Agent API:** (FastAPI)
      * **Location:** `luna-repo/core/utils/agent_api.py`
      * **Port:** `8080` (fixed)
      * **Features:** OpenAI-compatible API (`/v1/chat/completions`) for `simple_agent` and `passthrough_agent`. Auto-discovers tools from active extensions.
      * **Health:** `GET /healthz`
  * **MCP Server:** (Python + SSE)
      * **Location:** `luna-repo/core/utils/mcp_server.py`
      * **Port:** `8765` (fixed)
      * **Features:** Provides Server-Sent Events (SSE) stream for Model Context Protocol (ChatGPT/Claude integration). Exposes tools where `enabled_in_mcp: true`.
      * **Endpoint:** `GET /mcp/sse` (Requires `Authorization: Bearer {MCP_AUTH_TOKEN}`)
      * **Health:** `GET /healthz`

### **7. Configuration Management**

  * **`master_config.json`:** (`core/master_config.json`)
      * Source of truth. Only modified by `apply_updates.py`.
      * Stores `extensions` state, flat `tool_configs` namespace, `port_assignments`, and `external_services` status.
    <!-- end list -->
    ```json
    {
      "version": "1.0",
      "extensions": {
        "notes": { "enabled": true, "source": "github..." }
      },
      "tool_configs": {
        "NOTES_CREATE_note": { "enabled_in_mcp": true, "passthrough": false }
      },
      "port_assignments": {
        "core": { "hub_ui": 5173, ... },
        "extensions": { "notes": 5200 },
        "services": { "github_sync.webhook_receiver": 5300 }
      },
      "external_services": {
        "postgres": { "installed": true, "enabled": true }
      }
    }
    ```
  * **`state.json`:** (`supervisor/state.json`)
      * Ephemeral runtime state (PIDs, status, health failures). Git-ignored. Regenerated on startup.
    <!-- end list -->
    ```json
    {
      "services": {
        "hub_ui": { "pid": 1001, "port": 5173, "status": "running", "health_failures": 0 },
        "notes_ui": { "pid": 1004, "port": 5200, "status": "running", "health_failures": 0 },
        "github_sync_webhook": { "pid": 1005, "port": 5300, "status": "unhealthy", "health_failures": 1 }
      }
    }
    ```

### **8. Port Management**

  * **Core Services (Fixed):**
      * `5173`: Hub UI
      * `8080`: Agent API
      * `8765`: MCP Server
      * `9999`: Supervisor API
  * **Extension UIs (Dynamic):** `5200-5299`
  * **Extension Services (Dynamic):** `5300-5399` (only if `requires_port: true`)
  * **External Services (User-Configured):** e.g., `5432`, `6379`.
  * **Assignment Strategy:** On first enable, supervisor finds next available port (e.g., `5200` for UI, `5300` for service) and persists the assignment in `master_config.port_assignments`.
  * **`LUNA_PORTS` Env Var:** Supervisor exports a JSON string of `master_config.port_assignments` to all child processes.

### **9. Health Monitoring**

  * **Frequency:** Every 30 seconds.
  * **Logic (per service):**
    1.  Poll `GET /healthz`.
    2.  **On Success (200 OK):** `status: "running"`, reset failure/restart counters.
    3.  **On Failure (non-200/timeout):**
          * **1st Failure:** `status: "unhealthy"`.
          * **2nd Failure:** Stop process (SIGTERM -\> 5s -\> SIGKILL). Increment `restart_attempt` counter.
          * **If `restart_attempts < 2`:** Start process, reset failure counter.
          * **If `restart_attempts >= 2`:** `status: "failed"`. Stop monitoring.
  * **Manual Restart:** (via API) Resets all counters and restarts the service.

### **10. Agent System**

  * **Discovery:** Supervisor scans `core/agents/` for `agent.py` + `config.json`.
  * **Agent Types:**
      * `simple_agent`: LangChain ReAct agent for complex, multi-tool tasks.
      * `passthrough_agent`: Can use tools (honors `passthrough: true`) or respond naturally using the internal `DIRECT_RESPONSE` tool.
  * **`DIRECT_RESPONSE` Tool:**
    ```python
    def DIRECT_RESPONSE(message: str) -> Tuple[bool, str]:
        """Respond directly to the user without calling any tools."""
        return (True, f'{{"message": "{message}"}}')
    ```
  * **Tool Execution:** Retries tool execution up to 2 times on failure before returning an error to the agent.

### **11. Database**

  * **Default:** Bundled PostgreSQL external service.
  * **Connection:** Auto-generates `DATABASE_URL` and other vars in `.env`.
  * **Timezone:** All timestamps stored as **UTC**. All timestamps displayed as **America/New\_York**.
  * **Core Schema (`automation_memory`):**
    ```sql
    CREATE TABLE memories (
        id SERIAL PRIMARY KEY,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE scheduled_tasks (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        prompt TEXT NOT NULL,
        cron_expression TEXT NOT NULL,
        agent TEXT NOT NULL,
        enabled BOOLEAN DEFAULT TRUE,
        last_run TIMESTAMPTZ,
        next_run TIMESTAMPTZ
    );
    CREATE TABLE task_flows (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        steps JSONB NOT NULL, -- Array of {prompt, agent}
        enabled BOOLEAN DEFAULT TRUE
    );
    ```

### **12. API Specifications**

**12.1. Supervisor API (`:9999`)**

  * `GET /health`: Returns supervisor health.
  * `GET /services/status`: Returns full `state.json` content.
  * `GET /ports`: Returns `port_assignments` from `master_config`.
  * `POST /ports/assign`: (Internal) Assigns a new persistent port.
  * `POST /restart`: Queues a full system restart.
  * `POST /services/{service_name}/restart`: Manually restarts a specific service.

**12.2. Hub UI API (`:5173/api`)**

  * `GET /config/master`: Returns `master_config.json`.
  * `PATCH /config/master`: Queues a change to `master_config` (requires restart). Body: `{ "path": "extensions.notes.enabled", "value": true }`.
  * `GET /extensions`: List all installed extensions.
  * `POST /extensions/install`: Queues an extension install. Body: `{ "source": "github.com/...", "name": "ext_name" }`.
  * `DELETE /extensions/{name}`: Queues an extension uninstall.
  * `POST /extensions/{name}/enable` | `/disable`: Queues enable/disable.
  * `GET /external-services`: List all available/installed external services.
  * `POST /external-services/{name}/install`: Installs a service. Body: `{ "config": { "port": 5432, ... } }`.
  * `POST /external-services/{name}/uninstall`: Uninstalls a service.
  * `POST /external-services/{name}/start` | `/stop` | `/restart`: Manages service.
  * `POST /external-services/upload`: Uploads a new `service.json`. Body: `{ "service_definition": {...} }`.
  * `GET /env`: Returns all keys from `.env`.
  * `PATCH /env`: Hot-reloads `.env`. Body: `{ "OPENAI_API_KEY": "sk-new" }`.

**12.3. Agent API (`:8080`)**

  * `POST /v1/chat/completions`: OpenAI-compatible endpoint.
      * **Body:** `{ "model": "simple_agent", "messages": [...], "memory": [...] }`
      * **Response:** OpenAI-compatible chat completion object.

**12.4. MCP Server (`:8765`)**

  * `GET /mcp/sse`: (Requires `Authorization: Bearer {MCP_AUTH_TOKEN}`)
      * **Response:** `text/event-stream` with MCP-formatted tool definitions.

### **13. Extension Store**

  * **Structure:** Hosted in a `luna-extensions` monorepo containing a `registry.json`.
  * **`registry.json` Format:**
    ```json
    {
      "version": "1.0",
      "extensions": [
        {
          "name": "notes",
          "display_name": "Notes",
          "description": "Simple note-taking extension",
          "category": "productivity",
          "author": "Luna Team",
          "version": "10-20-25",
          "repository": "https://github.com/luna/extensions",
          "path": "extensions/notes",
          "tags": ["notes"]
        }
      ]
    }
    ```
  * **Installation:** `POST /api/extensions/install` is used for store, GitHub URL, and local path installs. All are queued for `apply_updates.py`.

### **14. Key Management**

  * **`.env` File:** `luna-repo/.env` (git-ignored). Stores `OPENAI_API_KEY`, `DATABASE_URL`, `MCP_AUTH_TOKEN`, etc.
  * **Hot Reload:** `PATCH /api/env` updates `.env` file and reloads environment variables in memory without a system restart.
  * **Required Secrets:** Extension `config.json` can specify `required_secrets: ["KEY_NAME"]`. The Hub UI will show a warning if these keys are missing from `.env`.

### **15. Testing Strategy**

  * **Phases:**
      * 1A: Core Infrastructure (Bootstrap, Supervisor)
      * 1B: Config & Sync
      * 1C: Service Management
      * 2A: Extension System
      * 2B: External Services
      * 2C: Agent System
  * **Reset State:** A script (`scripts/reset_test_env.sh`) is used to clear `state.json`, `update_queue.json`, reset `master_config.json`, and clear all user data/logs.
  * **Test Case Format:**
      * **Test ID:** `1A.1.1`
      * **Name:** Master Config Creation
      * **Setup:** `rm core/master_config.json`, start supervisor.
      * **Action:** Check if `master_config.json` exists.
      * **Verify:** File exists, contains required keys.
      * **Expected Output:** JSON blob with test status and verification booleans.

### **16. Deployment**

  * **MVP (Local):**
      * **Install:** `curl -sSL https://get.luna.ai/install.sh | bash`
      * **Access:** `http://localhost:5173` (Hub UI), `http://localhost:8080` (Agent API).
  * **Public Demo:**
      * **Architecture:** Caddy reverse proxy mapping a single domain to all internal ports.
      * **Example Caddyfile:**
        ```
        demo.luna.ai {
            reverse_proxy / localhost:5173
            reverse_proxy /api/* localhost:8080
            reverse_proxy /mcp/* localhost:8765
            reverse_proxy /ext/notes/* localhost:5200
            reverse_proxy /ext_service/grocy/* localhost:5303
        }
        ```
      * **Demo Mode:** `DEMO_MODE=true` env var disables config changes, installs, and `.env` editing.
