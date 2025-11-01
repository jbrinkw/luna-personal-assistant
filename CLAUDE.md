Luna Project Specification
==========================
Updated: 2025-10-31

---

Table of Contents
-----------------
1. Purpose & Scope
2. High-Level Architecture
3. Repository Layout & Conventions
4. Bootstrap & Process Orchestration
5. HTTP Surfaces & Networking
6. Configuration & Environment Management
7. Extensions
8. External Services
9. Agents & LLM Integration
10. Hub UI Experience
11. Installation & Operational Tasks
12. Logging, Monitoring, & Health
13. Testing Strategy
14. Divergences from Prior Documentation

---

1. Purpose & Scope
------------------
This document captures how the **current** Luna repository behaves at runtime. The previous `CLAUDE.md` described an older layout (e.g., `/opt/luna/luna-repo`, simple supervisor loop, bearer-token MCP). The system has evolved: we now run directly from this Git checkout, rely heavily on Caddy, enforce GitHub OAuth, and route nearly every interaction through a supervisor-managed API surface. Treat this document as the authoritative specification until the architecture shifts again.

---

2. High-Level Architecture
---------------------------
Luna runs as a constellation of cooperating processes launched and supervised by `supervisor/supervisor.py`:

- **Bootstrap (`luna.sh`)**: ensures a virtualenv exists, loads environment variables, cleans ports, and spawns the supervisor while preventing concurrent launches.
- **Supervisor**: starts and monitors all core services (Caddy, auth, Hub UI dev server, Agent API, MCP server), discovers extensions, and manages external services. It maintains `supervisor/state.json` and exposes a FastAPI control plane (`supervisor/api.py`).
- **Caddy reverse proxy**: the single HTTP entry point. It terminates TLS (where applicable), injects auth headers, rewrites OAuth discovery routes, and proxies traffic to the internal services.
- **GitHub OAuth auth service**: provides `/auth/login`/`/auth/callback`/`/auth/me`/`/auth/logout`, issues signed cookies, and (optionally) persists sessions in Postgres.
- **Agent API**: an OpenAI-compatible FastAPI server that auto-discovers LangChain tools and generates an `AGENT_API_KEY` stored in `.env`.
- **MCP server(s)**: the hub always runs a `main` FastMCP instance using GitHub OAuth and exposed at `/api/mcp`. Additional hub instances (e.g., `research`, `smarthome`) are optional; they run with API-key auth and are exposed at `/api/mcp-{name}`. Every hub shares the same tool discovery (local extensions + remote MCP servers).
- **Extensions & services**: each extension may include tools, a frontend (`ui/start.sh`), and background services. Ports are assigned deterministically and persisted in `master_config.json`.
- **External services**: Dockerized infrastructure components (Postgres, Grocy, etc.) managed via `ExternalServicesManager`; definitions live under `external_services/` with runtime metadata in `.luna/external_services.json`.

All long-lived processes are started within the repository root (not `/opt/luna/luna-repo`). You can inspect their PIDs and ports in `supervisor/state.json` and their log files under `logs/`.

---

3. Repository Layout & Conventions
----------------------------------
```
./
├── luna.sh                     # Bootstrap script (expects .venv/bin/python3)
├── requirements.txt            # Python dependencies
├── core/
│   ├── master_config.json      # Canonical configuration for extensions/services/tools
│   ├── agents/                 # Agent implementations
│   ├── scripts/                # CLI helpers (apply_updates, config_sync, init_db, etc.)
│   └── utils/                  # Core runtime modules (auth service, agent API, MCP server, etc.)
├── supervisor/
│   ├── supervisor.py           # Process orchestrator
│   ├── api.py                  # Supervisor FastAPI app
│   └── state.json              # Rewritten on startup with live PIDs/ports/status
├── extensions/                 # Extension packages (config, tools, optional UI/services)
├── external_services/          # Service definitions + persistent configs/data
├── hub_ui/                     # Vite/React Hub frontend
├── logs/                       # Runtime logs (supervisor.log, hub_ui.log, agent_api.log, auth_service.log, caddy.log, etc.)
├── .luna/                      # Generated artifacts (Caddyfile, external_services.json, routes)
├── install.sh                  # Interactive installer (ngrok / nip.io / custom domain)
├── install_config.json         # Saved installer selections (git-ignored)
└── tests/                      # Pytest suites & helpers
```

- **Git-ignored**: `.env`, `.venv`, `.luna/`, `logs/`, `extensions/*/config.json`, `external_services/*/config.json`, `external_services/*/data/`, `node_modules/`, `dist/`, caches, and compiled artifacts.
- **Virtualenv**: all processes run with `PYTHON_BIN=.venv/bin/python3`. `luna.sh` will abort if the virtualenv is missing.
- **Environment keys**: managed programmatically via `/api/supervisor/keys/*`; avoid editing `.env` manually unless you know the runtime will reload it.

---

4. Bootstrap & Process Orchestration
------------------------------------
### 4.1 `luna.sh`
- Sources `.env` (exporting values) before starting anything.
- Builds or cleans `.luna_lock` to prevent double launches; stale locks are removed automatically.
- Performs aggressive port cleanup for core ports (5173, 8080, 8443/443, 8765, 8766, 9999) plus extension/service ranges (5200-5399).
- Spawns the supervisor within the repo root, logging to `logs/supervisor.log`.
- Waits for `/health` on port 9999 with a configurable timeout; retries spawn if the process dies during startup.
- Handles SIGINT/SIGTERM by gracefully stopping tracked processes, reloading Caddy (if configured), and optionally preserving ngrok tunnels when running under systemd.

### 4.2 Supervisor Startup (Phases)
1. **Update Queue Check**: if `core/update_queue.json` exists, copy `core/scripts/apply_updates.py` to `/tmp`, create `.luna_updating`, spawn the script, and exit. The bootstrap loop waits for the flag to disappear before relaunching.
2. **Load/Create master_config**: ensures `core/master_config.json` exists, populating defaults (`deployment_mode`, `public_domain`, `extensions`, `tool_configs`, `port_assignments`, `mcp_servers`, `agent_presets`, `external_services`). Environment overrides (`DEPLOYMENT_MODE`, `PUBLIC_DOMAIN`) are applied after loading. Migration logic initializes `agent_presets: {}` if missing in existing configs.
3. **Config Sync**: invokes `config_sync.sync_all(repo_path)` to discover new extensions on disk, add them to `master_config`, and sync config/tool settings back to each extension.
4. **State Reset**: rewrites `supervisor/state.json` to `{"services": {}}`.
5. **Start Core Services** (in order):
   - `_start_caddy()`: installs Caddy if absent, generates `.luna/Caddyfile`, launches `caddy run --config ... --adapter caddyfile`, updates `state.json` after verifying the process stays alive.
   - `_start_auth_service()`: runs `core/utils/auth_service.py` on port 8765; GitHub credentials and optional username restrictions are read from environment.
   - `_start_hub_ui()`: ensures `npm install`/`pnpm install` has been executed, then runs `npm run dev` on port 5173.
   - `_start_agent_api()`: starts the OpenAI-compatible server on 8080, generating `AGENT_API_KEY` if missing and persisting it to `.env`.
   - `_start_mcp_server()`: launches FastMCP with GitHub OAuth on 8766; Caddy proxies it under `/api/mcp`.
6. **Enable Extensions**: for each `enabled` extension in `master_config` with a directory under `extensions/`:
   - Allocate deterministic ports (`5200-5299` for UIs, `5300-5399` for services) via `assign_port`.
   - Start `ui/start.sh` if present, logging to `logs/<extension>_ui.log`.
   - Iterate `services/<name>/`, read `service_config.json`, start `start.sh`, log to `logs/<extension>__service_<name>.log`.
7. **Load External Services**: load `.luna/external_services.json` and update `state.json` under `external_services`. (Note: auto-bootstrap from repo-root `*-docker.json` files is disabled; services must be installed via Hub UI or API upload.)
8. **Health Monitoring**: spawn a background thread that every 30 seconds executes `_health_check_external_services()` to run defined health checks, update registry entries, and restart unhealthy services if `restart_on_failure` is true.
9. **Operational Logs**: supervisor prints a startup summary including direct localhost URLs for quick debugging (Hub UI, auth, agent API, MCP, supervisor API).

### 4.3 Update Workflow (`core/scripts/apply_updates.py`)
- Queue schema:
  ```json
  {
    "created_at": "ISO8601",
    "operations": [
      {"type": "install", "target": "ext", "source": "github:user/repo"},
      {"type": "update", "target": "ext", "source": "upload:file.zip"},
      {"type": "delete", "target": "ext"},
      {"type": "install_external_service", "name": "postgres", ...},
      {"type": "update_core", "target_version": "latest"}
    ],
    "master_config": { ... }
  }
  ```
- `operations` run in deterministic phases: delete, install, update, external-service ops, core update, dependency installation, config sync.
- Supports GitHub monorepo installs (`github:user/repo:path/to/subdir`) and uploaded archives in `/tmp`.
- **Retry logic disabled**: Queued updates are applied immediately on next startup without retry checks or failure thresholds. The supervisor applies any queued updates found in `core/update_queue.json` without maintaining retry counters.
- On success rewrites `master_config.json`, removes the queue, and clears `.luna_updating`.

### 4.4 Supervisor API (`supervisor/api.py`)
- Exposes control endpoints for services, extensions, queue management, environment keys, external services, and system restart/shutdown.
- Requires `SUPERVISOR_API_TOKEN` for mutating operations when configured (Caddy injects the header in proxied requests).

---

5. HTTP Surfaces & Networking
-----------------------------
All external traffic should flow through Caddy; direct localhost access is possible for debugging but bypasses authentication and proxy header injection.

| Path / Prefix                 | Upstream              | Notes |
|------------------------------|-----------------------|-------|
| `/auth/*`                     | Auth service (8765)   | GitHub OAuth login/logout/session APIs |
| `/api/agent*`                 | Agent API (8080)      | Caddy injects `Authorization: Bearer <AGENT_API_KEY>` when available |
| `/.well-known/*`              | MCP (8766)            | Rewritten to `/api/.well-known/*` handled by FastMCP |
| `/api/mcp`, `/api/authorize`, `/api/token`, `/api/register` | MCP main (8766) | GitHub OAuth-protected hub (`main`) |
| `/api/mcp-{name}/*`           | Named MCP hubs        | API key required (`Authorization: Bearer <key>`) |
| `/api/supervisor/*`           | Supervisor API (9999) | Config/queue/env/external-service management |
| `/api/<extension>/*`          | Extension service ports | Populated from `master_config.port_assignments.services` |
| `/ext/<extension>/`           | Extension UI ports    | Trailing slash enforced by default unless disabled in `config.json` |
| `/ext_service/<slug>/`        | External service UI ports | Derived from `.luna/external_service_routes.json` |
| `/*` (catch-all)              | Hub UI dev server (5173) | React/Vite frontend |

Caddy decisions are governed by `core/utils/caddy_config_generator.py`, which inspects deployment mode (`ngrok`, `nip_io`, `custom_domain`), `public_domain`, and env vars (`AGENT_API_KEY`, `SUPERVISOR_API_TOKEN`, `MCP_AUTH_TOKEN`). The generated file is stored in `.luna/Caddyfile`.

---

6. Configuration & Environment Management
-----------------------------------------
### 6.1 `master_config.json`
Holds the authoritative view of extensions, tool configs, port assignments, and external service status. Example:
```
{
  "luna": {
    "version": "10-28-25",
    "timezone": "UTC",
    "default_llm": "gpt-4"
  },
  "deployment_mode": "custom_domain",
  "public_domain": "example.lunahub.dev",
  "extensions": {
    "automation_memory": {
      "enabled": true,
      "source": "local",
      "config": {}
    }
  },
  "tool_configs": {
    "MEMORY_GET_all": {
      "enabled_in_mcp": true,
      "passthrough": false
    }
  },
  "remote_mcp_servers": {
    "exa-search-server": {
      "server_id": "exa-search-server",
      "url": "https://mcp.exa.ai/mcp?api_key=...",
      "enabled": true,
      "tool_count": 2,
      "tools": {
        "web_search_exa": {
          "enabled": true,
          "docstring": "...",
          "input_schema": {...}
        }
      }
    }
  },
  "mcp_servers": {
    "main": {
      "name": "main",
      "port": 8766,
      "enabled": true,
      "tool_config": {
        "web_search_exa": { "enabled_in_mcp": true }
      }
    },
    "smarthome": {
      "name": "smarthome",
      "port": 8767,
      "enabled": true,
      "api_key": "...",  // supervisor also writes this to .env as MCP_SERVER_SMARTHOME_API_KEY
      "tool_config": {
        "home_assistant": { "enabled_in_mcp": true }
      }
    }
  },
  "agent_presets": {
    "smart_home_assistant": {
      "base_agent": "passthrough_agent",
      "enabled": true,
      "tool_config": {
        "home_assistant_get_state": { "enabled": true },
        "home_assistant_call_service": { "enabled": true },
        "web_search_exa": { "enabled": false }
      }
    }
  },
  "port_assignments": {
    "extensions": {
      "automation_memory": 5200
    },
    "services": {
      "automation_memory.backend": 5300
    }
  },
  "external_services": {
    "postgres": {
      "installed": true,
      "enabled": false
    }
  }
}
```

- Every non-`main` MCP server entry includes an `api_key`. The supervisor generates these (strong random values) and mirrors them into `.env` as `MCP_SERVER_<NAME>_API_KEY`. The Hub UI surfaces the key for copying/regeneration; only the `main` server relies on GitHub OAuth.

### 6.2 Config Sync (`core/scripts/config_sync.py`)
- Discovers extension directories and ensures each has an entry in `master_config.extensions` with `enabled`/`source` metadata.
- Writes back to `extensions/<name>/config.json`, preserving existing fields and `version` values (generating today’s date when missing).
- Syncs `tools/tool_config.json` entries for any tools defined in `master_config.tool_configs`.

### 6.3 Environment Keys
Managed exclusively through supervisor endpoints:
- `GET /api/supervisor/keys/list` → masked `.env` contents.
- `POST /api/supervisor/keys/set` → upsert key/value.
- `POST /api/supervisor/keys/delete` → remove key.
- `POST /api/supervisor/keys/upload-env` → merge uploaded `.env` file.
- `GET /api/supervisor/keys/required` → collect `required_secrets` from extension configs.
Calls rewrite `.env` and reload it in memory via `dotenv.load_dotenv(..., override=True)`.

---

7. Extensions
-------------
### 7.1 Filesystem Expectations
```
extensions/<name>/
├── config.json                 # Minimal manifest (name, required_secrets, auto_update, version, enabled, source, optional ui settings)
├── requirements.txt            # Optional Python deps
├── tools/
│   ├── tool_config.json        # Tool exposure settings (enabled_in_mcp, passthrough)
│   └── *_tools.py              # Tool implementations exporting TOOLS list
├── ui/
│   └── start.sh                # Receives port as $1; supervisor sets PATH to include .venv/bin and exports LUNA_PORTS
└── services/
    └── <service>/
        ├── service_config.json # {"name": "...", "requires_port": true, "health_check": "/healthz", "restart_on_failure": true}
        └── start.sh            # Receives port if requires_port=true
```

### 7.2 Tool Conventions
- Export a module-level `TOOLS` list containing callables.
- Functions typically return `(bool success, str json_payload)`; JSON helpers should use `json.dumps(..., ensure_ascii=False)` when emitting structured data.
- Docstrings must include `Example Prompt`, `Example Response`, and `Example Args` to aid LLM prompting.
- File-level `SYSTEM_PROMPT` strings are consumed by LangChain’s tool discovery.
- `tool_config.json` controls MCP exposure (`enabled_in_mcp`) and passthrough eligibility (`passthrough`).

### 7.3 Lifecycle & Queue Integration
- The Hub UI keeps a draft queue (`operations`, `master_config`) in memory; mutations (installs, updates, deletes) edit that draft.
- `POST /api/supervisor/queue/save` persists the queue; empty drafts remove the queue (`DELETE /api/supervisor/queue/current`).
- Once an operation is queued, the user must trigger a restart (`POST /api/supervisor/restart`). The supervisor spawns `apply_updates.py`, applies the queue, reruns config sync, and restarts services.

---

8. External Services
---------------------
### 8.1 Definitions
- Located under `external_services/<name>/service.json`.
- Bundled example definitions (`grocy-docker.json`, `postgres-docker.json`) exist in the repo root as reference/templates only; they are **not** auto-installed during startup.
- Services must be explicitly installed via Hub UI (External Services page) or API upload endpoint (`POST /api/external-services/upload`).
- Validated by `core/utils/external_service_schemas.ServiceDefinition` (supports both new `commands` object and legacy fields).
- Each definition may include:
  - Metadata (`name`, `display_name`, `description`, `category`, `version`).
  - `config_form`: fields presented in the Hub UI (type, label, default, help text).
  - `commands`: shell commands for `install`, `start`, `stop`, `restart`, `uninstall`, `health_check`, optional startup mode toggles.
  - `health_check_expected`: string or number used to verify health output.
  - `provides_vars` / `post_install_env`: environment variables to append to `.env`.
  - `ui`: metadata describing how to proxy the service UI (base path, slug, port or config field, scheme, strip_prefix, trailing slash handling, open mode).

### 8.2 Runtime Artifacts
- `.luna/external_services.json`: registry of installed services with status, timestamps, config/log paths.
- `.luna/external_service_routes.json`: UI routing metadata used by Caddy generator.
- `external_services/<name>/config.json`: persisted user-supplied config (git-ignored).
- `external_services/<name>/data/`: Docker volumes (git-ignored).

### 8.3 Supervisor API Endpoints
- `GET /api/external-services/available`
- `GET /api/external-services/installed`
- `GET /api/external-services/{name}`
- `POST /api/external-services/{name}/install`
- `POST /api/external-services/{name}/uninstall`
- `POST /api/external-services/{name}/start|stop|restart`
- `POST /api/external-services/{name}/enable|disable`
- `POST /api/external-services/upload`

Service health is monitored alongside extension services. Failures trigger restarts when `restart_on_failure` is true; status updates are logged to `.luna/external_services.json` and surfaced via API.

---

9. Agents & LLM Integration
---------------------------
### 9.1 Agent API (`core/utils/agent_api.py`)
- Discovers agent modules from `core/agents/`.
- Generates an `AGENT_API_KEY` on first run (format `sk-luna-<token>`), saves it to `.env`, and reuses it subsequently.
- Exposes `/v1/chat/completions` following OpenAI’s schema (supports streaming and non-streaming requests).
- Accepts `Authorization: Bearer <AGENT_API_KEY>` header; rejects other keys.
- Optional `X-Luna-Memory` header provides conversation memory to agents; the JSON body no longer carries a `memory` field.
- Tool discovery uses `extension_discovery.discover_extensions`, wrapping functions with LangChain `StructuredTool`s (Pydantic validation, retry logic).
- Includes custom LangChain callbacks for timing and trace capture.

### 9.2 Passthrough Agent (`core/agents/passthrough_agent/agent.py`)
- Planner/executor design with structured outputs describing tool calls.
- Honors `passthrough: true` in `tool_config.json` to allow autonomous tool execution.
- Provides a `DIRECT_RESPONSE` option for final answers when no tool is needed.

### 9.3 MCP Server (`core/utils/mcp_server.py`)
- FastMCP instance using `fastmcp.server.auth.providers.github.GitHubProvider`.
- Requires `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET`; fails fast if missing.
- Runs on `0.0.0.0:8766` with transport `streamable-http` by default.
- Caddy mounts the ASGI app under `/api/*`, rewriting OAuth discovery endpoints (`/.well-known/oauth-authorization-server`).
- Discovers MCP-enabled tools via `tool_discovery.get_mcp_enabled_tools()` which combines local extension tools and remote MCP server tools.
- Remote MCP tools are wrapped in `MCPRemoteTool` class and converted to proper function signatures with explicit parameters from JSON schemas for FastMCP registration.

### 9.4 Remote MCP Tools & Tool Discovery

**Overview:**
Luna supports loading tools from remote Smithery MCP servers, enabling access to external tool ecosystems (Exa search, Context7 docs, etc.) alongside local extension tools.

**Architecture Components:**

1. **`core/utils/remote_mcp_loader.py`** - Server Connection & Discovery
   - `extract_server_id_from_url(url)`: Extracts server identifier from URL (part between `//` and `api_key=`)
   - `async load_mcp_server(url)`: Connects via MCP protocol, fetches server name and tool schemas
   - `add_or_update_server(master_config, server_data)`: Adds/updates server in config, preserves enabled states
   - `async_add_or_update_server_from_url(master_config, url)`: Main entry point for adding servers

2. **`core/utils/remote_mcp_session_manager.py`** - Persistent Connections & Global Singleton
   - `PersistentMCPSession`: Manages single persistent MCP connection using background thread + event loop
   - `RemoteMCPSessionManager`: Manages multiple sessions
   - **Global Session Manager Singleton**: 
     - `get_global_session_manager()`: Returns singleton instance, initializes on first call from `master_config.json`
     - `reset_global_session_manager()`: Resets singleton for configuration changes
     - Thread-safe with locking (`_global_session_lock`)
     - Handles both sync and async contexts (uses background thread for async contexts)
     - Initialized once at startup, reused across all tool discovery calls
   - Maintains health tracking in `self._session_health` with connection status, timestamps, tool counts
   - Logs to `logs/remote_mcp_sessions.log` with detailed initialization info
   - Generates `logs/remote_mcp_tools_manifest.json` with comprehensive tool inventory and health status

3. **`core/utils/tool_discovery.py`** - Unified Tool Loading
   - `MCPRemoteTool`: Wrapper class that makes remote tools callable, stores server_id, tool_name, schemas
   - `get_all_tools()`: Returns tools grouped by source (extensions, remote_mcp_servers) for Hub UI
   - `get_mcp_enabled_tools(session_manager=None)`: Combines local + remote tools for MCP server registration
     - `session_manager` parameter now optional - automatically uses global session manager if None
   - `get_mcp_enabled_tools_for_server(server_name, master_config=None, session_manager=None)`: Server-specific tool loading
     - Automatically falls back to global session manager when `session_manager=None`
     - No need to pass session manager in most cases
   - Loads tools from all sources: local extensions via `extension_discovery`, remote servers from `master_config.remote_mcp_servers`

**Configuration:**
Remote MCP servers stored in `master_config.json` under `remote_mcp_servers`:
```json
{
  "server_id": "exa-search-server",
  "url": "https://mcp.exa.ai/mcp?api_key=...",
  "enabled": true,
  "tool_count": 2,
  "tools": {
    "tool_name": {
      "enabled": true,
      "docstring": "Tool description",
      "input_schema": {...},
      "output_schema": {...}
    }
  }
}
```

**Supervisor API Endpoints:**
- `POST /api/supervisor/remote-mcp/add` - Add remote MCP server by URL
- `GET /api/supervisor/remote-mcp/list` - List all remote servers
- `PATCH /api/supervisor/remote-mcp/{server_id}` - Update server/tool enabled status
- `DELETE /api/supervisor/remote-mcp/{server_id}` - Remove server
- `GET /api/supervisor/tools/all` - Get all tools from all sources

**Hub UI - Tool/MCP Manager (`/tools`):**
- Top-of-page selector lists all hub MCP servers; selecting one scopes the tool toggles below.
- Non-`main` hubs display their API key with copy + regenerate controls (keys are regenerated via Supervisor API).
- `main` remains GitHub OAuth only and cannot be renamed or deleted from the UI.
- Remote MCP server cards (existing UI) let you manage Smithery integrations; their tool toggles now enable/disable tools for the active hub server.
- Local extension cards retain the original enable/disable UI but also target the active hub server’s tool_config.
- Changes still require a Luna restart to take effect.

**Logging & Health:**
- `logs/remote_mcp_sessions.log`: Detailed connection logs, tool enumeration, initialization status
- `logs/remote_mcp_tools_manifest.json`: JSON manifest with:
  - Server health status (connected/error/disabled)
  - Tool counts (total/enabled)
  - Individual tool metadata (name, enabled, docstring, has_schema)
  - Timestamps for health checks

**Tool Registration Flow:**
1. MCP server startup initializes `RemoteMCPSessionManager` with `master_config` (for that server instance)
2. Session manager connects to all enabled remote servers, logs connection status
3. `tool_discovery.get_mcp_enabled_tools_for_server(server_name)` loads local + remote tools
   - If no session_manager passed, automatically uses global session manager singleton
   - Global session manager initialized lazily on first call
   - Handles both sync and async contexts transparently
4. Remote `MCPRemoteTool` instances converted to proper functions with explicit parameters from JSON schemas
5. All tools registered with FastMCP's `@tool` decorator
6. MCP server serves combined tool set to Anthropic Claude clients

**Global Session Manager Benefits:**
- **Efficient**: Remote MCP connections initialized once, reused across all tool discovery calls
- **Simple API**: No need to pass `session_manager` parameter - it's automatic
- **Thread-Safe**: Singleton protected with locks
- **Context-Aware**: Detects async contexts and initializes in background thread to avoid event loop conflicts
- **Persistent**: Connections maintained in background threads across entire application lifecycle
- Single source of truth: `master_config.json` (no config sync needed)
- Preserves enabled states across server updates
- Comprehensive health tracking and logging
- Seamless integration with local extension tools
- Tool calls delegated to remote MCP servers via session manager

### 9.5 Agent Presets

**Overview:**
Agent presets allow users to create custom agent configurations based on built-in agents with filtered tool access. This enables specialized agents (e.g., `smart_home_assistant`, `research_agent`) that have access only to relevant tools while maintaining the same runtime behavior as their base agent.

**Built-in vs Preset Agents:**
- **Built-in agents**: Core agent implementations in `core/agents/` (e.g., `passthrough_agent`, `simple_agent`) that have access to all tools
- **Preset agents**: User-created configurations stored in `master_config.json` that reference a built-in agent and define a custom tool subset

**Architecture:**

1. **Master Config Schema (`master_config.json`)**
```json
{
  "agent_presets": {
    "smart_home_assistant": {
      "base_agent": "passthrough_agent",
      "enabled": true,
      "tool_config": {
        "home_assistant_get_state": {
          "enabled": true
        },
        "home_assistant_call_service": {
          "enabled": true
        },
        "web_search_exa": {
          "enabled": false
        }
      }
    }
  }
}
```

Each preset includes:
- `base_agent`: Name of the built-in agent to use (e.g., `passthrough_agent`)
- `enabled`: Whether the preset is active
- `tool_config`: Map of tool names to `{enabled: boolean}` settings

2. **Supervisor API Endpoints (`supervisor/api.py`)**

Agent preset management:
- `GET /api/supervisor/agents/built-in` - List discovered built-in agents from `core/agents/`
- `GET /api/supervisor/agents/presets` - List user-created presets from `master_config`
- `GET /api/supervisor/agents/presets/{preset_name}/tools` - Get all available tools with enabled status for preset
- `POST /api/supervisor/agents/presets` - Create new preset (validates name, base agent, initializes tool config)
- `PATCH /api/supervisor/agents/presets/{preset_name}` - Update preset (name, base agent, or tool config)
- `DELETE /api/supervisor/agents/presets/{preset_name}` - Delete preset

Shared API key management:
- `GET /api/supervisor/agents/api-key` - Retrieve current `AGENT_API_KEY`
- `POST /api/supervisor/agents/api-key/regenerate` - Generate new API key and update `.env`

All preset operations update `master_config.json` and require a Luna restart to take effect.

3. **Agent API Integration (`core/utils/agent_api.py`)**

Preset loading and caching:
- At startup, `_init_agents()` loads `agent_presets` from `master_config.json`
- For each enabled preset:
  - Registers preset name in `AGENTS` dict pointing to base agent module
  - Caches enabled tool names in `_PRESET_TOOL_CACHE[preset_name]`
  - Stores metadata in `_PRESET_METADATA[preset_name]` (base agent, tool count)
- All available tools cached once in `_TOOL_CACHE` for efficient preset filtering

Model listing (`/v1/models`):
- Returns both built-in agents and presets
- Preset models include additional fields:
  - `is_preset`: true
  - `base_agent`: Name of underlying agent
  - `tool_count`: Number of enabled tools

Tool filtering:
- When `model` in chat completion matches a preset, `_PRESET_TOOL_CACHE[preset_name]` provides the allowed tool list
- Built-in agents continue to have access to all tools
- Tool filtering implementation pending agent-side integration (currently logged but not enforced at runtime)

4. **Hub UI - Tool/MCP Manager (`hub_ui/src/pages/MCPToolManager.jsx`)**

Unified layout with mode toggle:
- **Mode Toggle**: Top-right buttons switch between `MCP` and `Agent Presets` modes
- **Shared Structure**: Single layout with conditional content based on mode:
  1. **Selector Pills** - MCP servers (mode=mcp) or Agent presets (mode=agent)
  2. **Quick Actions** - Enable/disable all tools for active server/preset
  3. **Management Grid** - 2-column layout:
     - **Left**: Manage active item (rename, delete, API key display with eye button for presets)
     - **Right**: Create new item (server name or preset name + base agent selector)
  4. **Add Remote MCP Server** - Shared across both modes
  5. **Remote MCP Tools** - Toggle tools from Smithery MCP servers
  6. **Local Extension Tools** - Toggle tools from local extensions

Mode-aware behavior:
- Selector checks `activeServer` (MCP) or `activePreset` (agent)
- Tool toggles call `toggleServerTool()` (MCP) or `togglePresetTool()` (agent)
- Quick Actions label shows "Quick Actions for {server/preset}:"
- Subtitle shows "Active MCP: X" or "Active Preset: X"

State management:
- `builtInAgents`: List of agents discovered from `core/agents/`
- `agentPresets`: List of user presets with name, base_agent, tool_count
- `activePreset`: Currently selected preset
- `presetTools`: Tool configurations for active preset
- `sharedApiKey`: Agent API key (hidden by default, toggle with eye button)

API integration:
- `loadBuiltInAgents()` - Fetch from `/api/supervisor/agents/built-in`
- `loadAgentPresets()` - Fetch from `/api/supervisor/agents/presets`
- `loadPresetTools(presetName)` - Fetch from `/api/supervisor/agents/presets/{name}/tools`
- `createAgentPreset()` - POST to `/api/supervisor/agents/presets`
- `updateAgentPreset(name, updates)` - PATCH to `/api/supervisor/agents/presets/{name}`
- `deleteAgentPreset(name)` - DELETE to `/api/supervisor/agents/presets/{name}`
- `togglePresetTool(toolName, currentState)` - Updates tool config and saves via PATCH

5. **Hub UI - Dashboard (`hub_ui/src/pages/Dashboard.jsx`)**

Discovered Agents card displays:
- **Built-in Agents** section: Lists agent names
- **Agent Presets** section: Lists each preset with:
  - Preset name (bold)
  - Base agent: `{base_agent}`
  - Tool count: `{tool_count} tools`
- Total count: Built-in + Presets

**Workflow:**
1. User navigates to Tool Manager (`/tools`)
2. Toggle to "Agent Presets" mode
3. Create new preset by selecting name and base agent
4. Select preset from pills to activate it
5. Toggle individual tools on/off for that preset
6. Use Quick Actions to enable/disable all tools at once
7. Copy/regenerate shared API key as needed
8. Changes persist to `master_config.json` (require restart to take effect)
9. Preset appears in `/v1/models` API response after restart
10. OpenAI clients can request preset by name like any other model

**Tool Access Filtering:**
- Current implementation caches allowed tools but requires agent-side integration for runtime enforcement
- Future enhancement will pass `allowed_tool_names` to agent's `initialize_runtime()` or modify `extension_discovery` to filter based on preset config

---

10. Hub UI Experience
---------------------
- Built with Vite/React; served through Caddy catch-all.
- `AuthContext` checks `GET /auth/me`, redirects to `/auth/login`, and logs out via `POST /auth/logout`.
- `ConfigContext` loads `master_config` (`/api/supervisor/config/master`), tracks draft queue state, and persists changes (`/api/supervisor/queue/save`).
- Extension Manager supports:
  - ZIP upload: `ExtensionsAPI.upload` posts to `/api/supervisor/extensions/upload`, returning a temporary filename stored in queue operations (`source: "upload:filename.zip"`).
  - Git install: user-entered strings converted to `github:` sources (`github:user/repo` or `github:user/repo:path/subdir`).
  - Enable/disable toggles update the queue by editing `master_config.extensions[<name>].enabled`.
- Tool Manager (`/tools`) provides unified interface with MCP/Agent Presets mode toggle:
  - **MCP Mode**: Manage local MCP servers, add remote Smithery MCP servers, toggle tools per server
  - **Agent Presets Mode**: Create/manage agent presets based on built-in agents, filter tool access per preset
  - Both modes share the same tool selection UI (remote MCP tools + local extension tools)
  - Quick Actions for bulk enable/disable all tools for active server/preset
  - Viewing tool descriptions and schemas
- Header keeps a persistent Update Manager control beside Restart; it always links to `/queue` and expands with a pending-change count when updates are queued. The Dashboard quick-actions row features Tool Manager (`/tools`) in place of the former Update Manager tile.
- External Services pages call `/api/external-services/*` endpoints for install/start/stop and display UI links generated by Caddy.
- Environment Key Manager interacts exclusively with `/api/supervisor/keys/*` endpoints.
- System controls (restart/shutdown) use `/api/supervisor/restart` and `/api/supervisor/shutdown`.

---

11. Installation & Operational Tasks
------------------------------------
### 11.1 Installer (`install.sh`)
- Must be executed with sudo (`sudo ./install.sh`).
- Installs prerequisite packages (Python, pip, Node, pnpm/npm, Docker, jq, etc.).
- Prompts for deployment mode:
  - `ngrok`: requires `ngrok.api_key` and `ngrok.domain` in `install_config.json`.
  - `nip_io`: expects ports 80/443 open; auto-detects public IP.
  - `custom_domain`: user supplies domain and ensures DNS A record.
- Writes `install_config.json` with choices and secrets; configures `.env`/systemd as needed.
- Creates `.venv`, installs Python requirements, and runs database setup scripts upon request.

### 11.2 Database Initialization
- `core/scripts/create_db.py`: creates the database specified by `.env` (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).
- `core/scripts/init_db.py`: executes SQL migrations to create tables for automation_memory (memories, task_flows, schedules, etc.).

### 11.3 Operational Scripts
- `core/scripts/install_deps.py`: install extension dependencies (Python/npm) when triggered via queue operations.
- `core/scripts/reload_caddy.sh`: manual hook to reload Caddy (invoked by supervisor and bootstrap).
- `core/scripts/kill_luna.sh`, `kill_luna.sh`: forceful shutdown helpers when automation fails.

---

12. Logging, Monitoring, & Health
---------------------------------
- Log files reside in `logs/` (supervisor.log, hub_ui.log, agent_api.log, auth_service.log, mcp_server.log, caddy.log, extension/service logs, remote_mcp_sessions.log). External-service logs are under `.luna/logs/`.
- Remote MCP session logs:
  - `logs/remote_mcp_sessions.log`: Detailed connection logs, tool discovery, health status
  - `logs/remote_mcp_tools_manifest.json`: JSON manifest with server health, tool counts, and individual tool metadata
- Supervisor health endpoint: `GET /api/supervisor/health` (proxied via Caddy at `/api/supervisor/health`).
- Supervisor state file: `supervisor/state.json` enumerates each service with PID, port, status, and last health check time.
- Health monitoring thread (within supervisor) checks external services every 30 seconds and restarts unhealthy services when allowed.
- Bootstrap keeps attempting to restart the supervisor if `/health` fails repeatedly, cleaning ports between attempts.

---

13. Testing Strategy
--------------------
- Pytest suite organized into phases (`tests/phase_1a`, `phase_1b`, `phase_1c`, etc.) plus integration tests (agent API, external services, prompt runner).
- Shell helpers (`tests/run_db_tests.sh`, `tests/simple_install_test.sh`, `tests/reset_phase1.sh`) cover end-to-end flows.
- CI expectations: tests should pass after any change to supervisor, agent API, extension discovery, or external-service logic.

---

14. Divergences from Prior Documentation
----------------------------------------
1. **Runtime Location**: The system runs directly from the repository root. The `/opt/luna/luna-repo` hierarchy in earlier docs is obsolete.
2. **Supervisor Behavior**: No longer a simple restart loop; now includes queue retries, Caddy management, GitHub auth, and background health threads.
3. **Caddy + OAuth**: All HTTP surfaces sit behind Caddy with GitHub OAuth for both Hub UI and MCP. Prior bearer-token/SSE references are invalid.
4. **Update Queue Schema**: Uses an `operations` array with typed entries instead of dotted `path` changes.
5. **Environment Management**: `/api/supervisor/keys/*` replaces the old `PATCH /api/env` hot reload endpoint.
6. **Extension Services**: Implemented via `service_config.json` + `start.sh`; the previously documented in-extension `service.json` command structure is not used.
7. **Logging Paths**: Core logs live in `logs/`; `.luna/` stores generated Caddy and external-service metadata.
8. **Hub UI APIs**: Now call supervisor endpoints directly; `/api/extensions/...` (old spec) does not exist.
9. **DEMO_MODE**: Mentioned in legacy docs but not implemented in current code paths.

Keep this document synchronized with future changes to supervisor startup order, proxy generation, queue semantics, or API contracts to prevent the Hub UI, deployment scripts, and external integrations from drifting.
