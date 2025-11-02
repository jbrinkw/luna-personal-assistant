# Configuration Reference

Complete reference for Luna's configuration files and environment variables.

---

## master_config.json

The authoritative configuration file for Luna. Located at `core/master_config.json`.

### Top-Level Structure

```json
{
  "luna": {...},
  "deployment_mode": "...",
  "public_domain": "...",
  "extensions": {...},
  "tool_configs": {...},
  "remote_mcp_servers": {...},
  "mcp_servers": {...},
  "agent_presets": {...},
  "port_assignments": {...},
  "external_services": {...}
}
```

---

### luna

Core Luna metadata.

```json
{
  "version": "10-28-25",
  "timezone": "UTC",
  "default_llm": "gpt-4"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Luna release version |
| `timezone` | string | System timezone (e.g., "UTC", "America/New_York") |
| `default_llm` | string | Default LLM model identifier |

---

### deployment_mode

Determines how Luna is exposed to the internet.

**Values:**
- `ngrok` - Uses ngrok tunnel with custom domain
- `nip_io` - Uses nip.io wildcard DNS (port 80/443 required)
- `custom_domain` - User-configured domain with DNS A record

**Example:**
```json
{
  "deployment_mode": "custom_domain",
  "public_domain": "luna.example.com"
}
```

---

### extensions

Map of installed extensions.

**Structure:**
```json
{
  "extension_name": {
    "enabled": true,
    "source": "local|github:user/repo|upload:file.zip",
    "config": {...}
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether extension is active |
| `source` | string | Install source (local, GitHub URL, or uploaded file) |
| `config` | object | Extension-specific configuration (optional) |

**Example:**
```json
{
  "automation_memory": {
    "enabled": true,
    "source": "local",
    "config": {}
  },
  "home_assistant": {
    "enabled": true,
    "source": "github:user/luna-home-assistant",
    "config": {
      "default_timeout": 30
    }
  }
}
```

---

### tool_configs

Global tool enable/disable settings.

**Structure:**
```json
{
  "tool_name": {
    "enabled_in_mcp": true,
    "passthrough": false
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `enabled_in_mcp` | boolean | Tool available in MCP servers |
| `passthrough` | boolean | Agent can auto-execute without user confirmation |

**Example:**
```json
{
  "memory_get": {
    "enabled_in_mcp": true,
    "passthrough": true
  },
  "web_search": {
    "enabled_in_mcp": true,
    "passthrough": false
  }
}
```

---

### remote_mcp_servers

Smithery MCP server integrations.

**Structure:**
```json
{
  "server_id": {
    "server_id": "exa-search-server",
    "url": "https://mcp.exa.ai/mcp?api_key=...",
    "enabled": true,
    "tool_count": 2,
    "tools": {
      "tool_name": {
        "enabled": true,
        "docstring": "...",
        "input_schema": {...},
        "output_schema": {...}
      }
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `server_id` | string | Unique identifier extracted from URL |
| `url` | string | Complete Smithery MCP URL (includes API key) |
| `enabled` | boolean | Server is active |
| `tool_count` | number | Number of tools discovered |
| `tools` | object | Map of tool configurations |

---

### mcp_servers

Local MCP hub configurations.

**Structure:**
```json
{
  "main": {
    "name": "main",
    "port": 8766,
    "enabled": true,
    "tool_config": {...}
  },
  "custom_hub": {
    "name": "custom_hub",
    "port": 8767,
    "enabled": true,
    "api_key": "...",
    "tool_config": {...}
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Hub identifier |
| `port` | number | Port number |
| `enabled` | boolean | Hub is active |
| `api_key` | string | API key (auto-generated for non-main hubs) |
| `tool_config` | object | Per-hub tool enable/disable settings |

**Notes:**
- `main` hub uses GitHub OAuth (no API key)
- Other hubs require API key authentication
- API keys are also stored in `.env` as `MCP_SERVER_<NAME>_API_KEY`

---

### agent_presets

Custom agent configurations with filtered tool access.

**Structure:**
```json
{
  "preset_name": {
    "base_agent": "passthrough_agent",
    "enabled": true,
    "tool_config": {
      "tool_name": {"enabled": true}
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `base_agent` | string | Built-in agent to use (e.g., "passthrough_agent") |
| `enabled` | boolean | Preset is active |
| `tool_config` | object | Tool enable/disable for this preset |

**Example:**
```json
{
  "smart_home_assistant": {
    "base_agent": "passthrough_agent",
    "enabled": true,
    "tool_config": {
      "home_assistant_get_state": {"enabled": true},
      "home_assistant_call_service": {"enabled": true},
      "web_search": {"enabled": false}
    }
  }
}
```

---

### port_assignments

Deterministic port allocation for extensions and services.

**Structure:**
```json
{
  "extensions": {
    "extension_name": 5200
  },
  "services": {
    "extension_name.service_name": 5300
  }
}
```

| Range | Purpose |
|-------|---------|
| `5200-5299` | Extension UIs |
| `5300-5399` | Extension services |

**Notes:**
- Ports are assigned automatically during extension installation
- Persisted to prevent conflicts on restart

---

### external_services

Installed external service status.

**Structure:**
```json
{
  "service_name": {
    "installed": true,
    "enabled": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `installed` | boolean | Service definition exists |
| `enabled` | boolean | Auto-start on Luna boot |

Full service details are in `.luna/external_services.json`.

---

## Extension config.json

Located at `extensions/<name>/config.json`.

### Structure

```json
{
  "name": "my_extension",
  "version": "2025-11-01",
  "enabled": true,
  "source": "local",
  "auto_update": false,
  "required_secrets": ["API_KEY", "DB_PASSWORD"],
  "ui": {
    "strip_prefix": false,
    "enforce_trailing_slash": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Extension identifier (must match directory name) |
| `version` | string | Version string (usually YYYY-MM-DD) |
| `enabled` | boolean | Extension is active |
| `source` | string | Install source |
| `auto_update` | boolean | Check for updates (GitHub sources only) |
| `required_secrets` | array | Environment variables needed |
| `ui.strip_prefix` | boolean | Remove `/ext/<name>` before proxying |
| `ui.enforce_trailing_slash` | boolean | Redirect to add trailing slash |

---

## Tool tool_config.json

Located at `extensions/<name>/tools/tool_config.json`.

### Structure

```json
{
  "tool_name": {
    "enabled_in_mcp": true,
    "passthrough": false
  }
}
```

See `tool_configs` in master_config for field descriptions.

---

## External Service service.json

Located at `external_services/<name>/service.json`.

### Structure

```json
{
  "name": "postgres",
  "display_name": "PostgreSQL Database",
  "description": "PostgreSQL database server",
  "category": "database",
  "version": "16",
  "config_form": [...],
  "commands": {...},
  "health_check_expected": "accepting connections",
  "provides_vars": ["DB_HOST", "DB_PORT"],
  "post_install_env": {...},
  "ui": {...}
}
```

### config_form

Array of form fields for user configuration.

```json
[
  {
    "name": "POSTGRES_PASSWORD",
    "type": "password",
    "label": "Database Password",
    "default": "",
    "help": "Password for the postgres user",
    "required": true
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Environment variable name |
| `type` | string | Field type (text, password, number, select) |
| `label` | string | UI label |
| `default` | any | Default value |
| `help` | string | Help text |
| `required` | boolean | Field is required |
| `options` | array | Options for select fields |

### commands

Service lifecycle commands.

```json
{
  "install": "docker-compose up -d",
  "start": "docker-compose start",
  "stop": "docker-compose stop",
  "restart": "docker-compose restart",
  "uninstall": "docker-compose down -v",
  "health_check": "docker exec postgres pg_isready"
}
```

### ui

Service UI proxy configuration.

```json
{
  "base_path": "/ext_service/grocy",
  "slug": "grocy",
  "port": 8081,
  "scheme": "http",
  "strip_prefix": false,
  "enforce_trailing_slash": true,
  "open_mode": "new_tab"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `base_path` | string | URL path prefix |
| `slug` | string | URL-safe identifier |
| `port` | number or string | Port number or config field name |
| `scheme` | string | http or https |
| `strip_prefix` | boolean | Remove base_path before proxying |
| `enforce_trailing_slash` | boolean | Redirect to add trailing slash |
| `open_mode` | string | "new_tab" or "same_window" |

---

## Environment Variables

Environment variables are stored in `.env` (git-ignored).

### Core Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DEPLOYMENT_MODE` | ngrok, nip_io, or custom_domain | Yes |
| `PUBLIC_DOMAIN` | Your public domain | Yes |
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID | Yes |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app secret | Yes |
| `ALLOWED_GITHUB_USERNAME` | Restrict access to specific user | No |

### Service Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AGENT_API_KEY` | Agent API authentication | Auto-generated |
| `MCP_GITHUB_CLIENT_ID` | MCP GitHub OAuth client ID | Yes |
| `MCP_GITHUB_CLIENT_SECRET` | MCP GitHub OAuth secret | Yes |
| `MCP_SERVER_<NAME>_API_KEY` | Named MCP hub API keys | Auto-generated |
| `SUPERVISOR_API_TOKEN` | Supervisor API auth | Optional |

### Database Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DB_HOST` | Database host | If using Postgres |
| `DB_PORT` | Database port | If using Postgres |
| `DB_NAME` | Database name | If using Postgres |
| `DB_USER` | Database user | If using Postgres |
| `DB_PASSWORD` | Database password | If using Postgres |
| `DATABASE_URL` | Full connection string | Alternative |

### LLM Provider Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | If using OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | If using Claude |

### Extension Variables

Extensions define their own required variables in `config.json` under `required_secrets`. Check each extension's README for details.

---

## Configuration Management

### Via Hub UI

1. Navigate to Environment Keys page
2. Add/update/delete keys
3. Changes take effect immediately (no restart needed)

### Via API

Use the `/api/supervisor/keys/*` endpoints. See [API Reference](api.md#environment-keys).

### Manual Editing

Edit `.env` directly, then restart Luna:

```bash
./luna.sh
```

**Warning:** Manual edits bypass validation. Use the UI or API when possible.

---

## Configuration Priority

1. **Environment variables** override everything
2. **master_config.json** provides defaults
3. **Extension configs** inherit from master_config
4. **Tool configs** cascade: master → MCP server → agent preset

---

## Best Practices

- Use the Hub UI or API to manage configuration (automatic validation)
- Keep `.env` in `.gitignore` (secrets should never be committed)
- Backup `master_config.json` before major changes
- Use agent presets instead of duplicating tool configs
- Document custom configuration in extension READMEs
