Luna Project Specification
==========================
Updated: 2025-10-28

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
- **MCP server**: a FastMCP instance using GitHub OAuth, surfaced externally through Caddy under `/api/mcp`.
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
2. **Load/Create master_config**: ensures `core/master_config.json` exists, populating defaults (`deployment_mode`, `public_domain`, `extensions`, `tool_configs`, `port_assignments`, `external_services`). Environment overrides (`DEPLOYMENT_MODE`, `PUBLIC_DOMAIN`) are applied after loading.
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
- Maintains retry metadata in `core/update_retry_count.json` (max 3 attempts). Stuck queues are renamed to `update_queue_failed.json` and supervisor startup proceeds without applying them.
- On success rewrites `master_config.json`, removes the queue and retry file, and clears `.luna_updating`.

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
| `/api/mcp`, `/api/authorize`, `/api/token`, `/api/register` | MCP (8766) | GitHub OAuth-protected integration for Anthropic clients |
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
- Discovers MCP-enabled tools via `extension_discovery.get_mcp_tools()`.

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
- Log files reside in `logs/` (supervisor.log, hub_ui.log, agent_api.log, auth_service.log, mcp_server.log, caddy.log, extension/service logs). External-service logs are under `.luna/logs/`.
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
