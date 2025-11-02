# API Reference

Complete reference for Luna's HTTP APIs.

---

## Base URLs

- **Public (via Caddy)**: `https://your-domain.com/api`
- **Local Development**: `http://localhost:9999` (supervisor), `http://localhost:8080` (agent), etc.

All production traffic should go through Caddy for authentication and proper routing.

---

## Supervisor API

The supervisor manages Luna's core services, extensions, and configuration.

**Base Path**: `/api/supervisor`

### Configuration

#### Get Master Config
```http
GET /api/supervisor/config/master
```

Returns the complete `master_config.json`.

**Response:**
```json
{
  "luna": {"version": "...", "timezone": "UTC"},
  "deployment_mode": "custom_domain",
  "public_domain": "example.com",
  "extensions": {...},
  "tool_configs": {...},
  "mcp_servers": {...},
  "agent_presets": {...}
}
```

#### Update Master Config
```http
POST /api/supervisor/config/master
Content-Type: application/json
```

**Body:** Complete or partial master_config object

**Response:** `{"status": "success", "message": "..."}`

---

### Environment Keys

#### List Keys
```http
GET /api/supervisor/keys/list
```

Returns all `.env` keys with masked values.

**Response:**
```json
{
  "GITHUB_CLIENT_ID": "Ov23li***",
  "OPENAI_API_KEY": "sk-***",
  "DB_PASSWORD": "***"
}
```

#### Set Key
```http
POST /api/supervisor/keys/set
Content-Type: application/json

{
  "key": "OPENAI_API_KEY",
  "value": "sk-..."
}
```

#### Delete Key
```http
POST /api/supervisor/keys/delete
Content-Type: application/json

{"key": "OLD_API_KEY"}
```

#### Upload .env File
```http
POST /api/supervisor/keys/upload-env
Content-Type: multipart/form-data

file: <.env file>
```

Merges uploaded keys with existing environment.

#### Get Required Secrets
```http
GET /api/supervisor/keys/required
```

Returns list of required environment variables from all enabled extensions.

**Response:**
```json
{
  "required_secrets": [
    {"key": "OPENAI_API_KEY", "source": "core"},
    {"key": "HA_TOKEN", "source": "home_assistant"}
  ]
}
```

---

### Extensions

#### Upload Extension
```http
POST /api/supervisor/extensions/upload
Content-Type: multipart/form-data

file: <extension.zip>
```

**Response:**
```json
{
  "status": "success",
  "filename": "extension_abc123.zip",
  "message": "Extension uploaded. Add to queue to install."
}
```

#### Get Extension Info
```http
GET /api/supervisor/extensions/{extension_name}
```

Returns extension metadata and status.

---

### Update Queue

#### Get Current Queue
```http
GET /api/supervisor/queue/current
```

**Response:**
```json
{
  "created_at": "2025-11-01T12:00:00Z",
  "operations": [
    {
      "type": "install",
      "target": "my_extension",
      "source": "github:user/repo"
    }
  ],
  "master_config": {...}
}
```

#### Save Queue
```http
POST /api/supervisor/queue/save
Content-Type: application/json

{
  "operations": [...],
  "master_config": {...}
}
```

#### Delete Queue
```http
DELETE /api/supervisor/queue/current
```

Clears all pending operations.

---

### Services

#### List Services
```http
GET /api/supervisor/services
```

Returns status of all running services (PIDs, ports, health).

#### Restart Service
```http
POST /api/supervisor/services/{service_name}/restart
```

#### Stop Service
```http
POST /api/supervisor/services/{service_name}/stop
```

#### Start Service
```http
POST /api/supervisor/services/{service_name}/start
```

---

### External Services

#### List Available Services
```http
GET /api/external-services/available
```

Returns service definitions from `external_services/*/service.json`.

#### List Installed Services
```http
GET /api/external-services/installed
```

#### Get Service Details
```http
GET /api/external-services/{service_name}
```

#### Install Service
```http
POST /api/external-services/{service_name}/install
Content-Type: application/json

{
  "config": {
    "POSTGRES_PASSWORD": "secure123",
    "POSTGRES_DB": "mydb"
  }
}
```

#### Uninstall Service
```http
POST /api/external-services/{service_name}/uninstall
```

#### Start/Stop/Restart Service
```http
POST /api/external-services/{service_name}/start
POST /api/external-services/{service_name}/stop
POST /api/external-services/{service_name}/restart
```

#### Enable/Disable Service
```http
POST /api/external-services/{service_name}/enable
POST /api/external-services/{service_name}/disable
```

#### Upload Service Definition
```http
POST /api/external-services/upload
Content-Type: multipart/form-data

file: <service.json>
```

---

### Tools & MCP

#### List All Tools
```http
GET /api/supervisor/tools/all
```

Returns tools from all sources (extensions, remote MCP servers).

**Response:**
```json
{
  "extensions": {
    "automation_memory": [
      {"name": "memory_get", "enabled": true, "docstring": "..."}
    ]
  },
  "remote_mcp_servers": {
    "exa-search": [
      {"name": "web_search", "enabled": true}
    ]
  }
}
```

#### Add Remote MCP Server
```http
POST /api/supervisor/remote-mcp/add
Content-Type: application/json

{
  "url": "https://mcp.exa.ai/mcp?api_key=..."
}
```

#### List Remote MCP Servers
```http
GET /api/supervisor/remote-mcp/list
```

#### Update Remote MCP Server
```http
PATCH /api/supervisor/remote-mcp/{server_id}
Content-Type: application/json

{
  "enabled": true,
  "tools": {
    "tool_name": {"enabled": false}
  }
}
```

#### Delete Remote MCP Server
```http
DELETE /api/supervisor/remote-mcp/{server_id}
```

---

### Agent Presets

#### List Built-in Agents
```http
GET /api/supervisor/agents/built-in
```

**Response:**
```json
{
  "agents": ["passthrough_agent", "simple_agent"]
}
```

#### List Agent Presets
```http
GET /api/supervisor/agents/presets
```

**Response:**
```json
{
  "presets": [
    {
      "name": "smart_home_assistant",
      "base_agent": "passthrough_agent",
      "enabled": true,
      "tool_count": 5
    }
  ]
}
```

#### Get Preset Tools
```http
GET /api/supervisor/agents/presets/{preset_name}/tools
```

Returns all available tools with enabled status for this preset.

#### Create Agent Preset
```http
POST /api/supervisor/agents/presets
Content-Type: application/json

{
  "name": "research_agent",
  "base_agent": "passthrough_agent"
}
```

#### Update Agent Preset
```http
PATCH /api/supervisor/agents/presets/{preset_name}
Content-Type: application/json

{
  "name": "new_name",
  "base_agent": "passthrough_agent",
  "tool_config": {
    "web_search": {"enabled": true},
    "memory_get": {"enabled": false}
  }
}
```

#### Delete Agent Preset
```http
DELETE /api/supervisor/agents/presets/{preset_name}
```

#### Get Agent API Key
```http
GET /api/supervisor/agents/api-key
```

**Response:**
```json
{
  "api_key": "sk-luna-..."
}
```

#### Regenerate Agent API Key
```http
POST /api/supervisor/agents/api-key/regenerate
```

Generates new API key and updates `.env`.

---

### System Control

#### Health Check
```http
GET /api/supervisor/health
```

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "caddy": "running",
    "hub_ui": "running",
    "agent_api": "running"
  }
}
```

#### Restart Luna
```http
POST /api/supervisor/restart
```

Applies queued updates and restarts all services.

#### Shutdown Luna
```http
POST /api/supervisor/shutdown
```

Graceful shutdown of all services.

---

## Agent API

OpenAI-compatible chat completion API.

**Base Path**: `/api/agent` (via Caddy) or `http://localhost:8080` (direct)

### Authentication

All requests require:
```http
Authorization: Bearer <AGENT_API_KEY>
```

Get your key from `.env` or `/api/supervisor/agents/api-key`.

### Chat Completions

#### Create Chat Completion
```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer sk-luna-...

{
  "model": "passthrough_agent",
  "messages": [
    {"role": "user", "content": "What's the weather?"}
  ],
  "stream": false
}
```

**Optional Headers:**
- `X-Luna-Memory`: JSON string with conversation memory

**Response (Non-Streaming):**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "passthrough_agent",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "The weather is..."
    },
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 10, "completion_tokens": 20}
}
```

**Streaming Response:**
Server-sent events (SSE) with `data: {...}` lines.

### List Models

#### Get Available Models
```http
GET /v1/models
Authorization: Bearer sk-luna-...
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "passthrough_agent",
      "object": "model",
      "created": 1234567890,
      "owned_by": "luna"
    },
    {
      "id": "smart_home_assistant",
      "object": "model",
      "created": 1234567890,
      "owned_by": "luna",
      "is_preset": true,
      "base_agent": "passthrough_agent",
      "tool_count": 5
    }
  ]
}
```

---

## Auth Service

Handles GitHub OAuth authentication.

**Base Path**: `/auth`

### Login
```http
GET /auth/login?redirect_uri=/dashboard
```

Redirects to GitHub OAuth flow.

### OAuth Callback
```http
GET /auth/callback?code=...&state=...
```

GitHub redirects here after authentication. Sets session cookie.

### Get Current User
```http
GET /auth/me
```

**Response:**
```json
{
  "username": "jbrinkw",
  "avatar_url": "https://...",
  "authenticated": true
}
```

### Logout
```http
POST /auth/logout
```

Clears session cookie.

---

## MCP Server

Anthropic MCP server for Claude Desktop and other MCP clients.

**Base Path**: `/api/mcp` (main hub) or `/api/mcp-{name}` (named hubs)

### Authentication

- **Main Hub**: GitHub OAuth (handled by FastMCP)
- **Named Hubs**: API key in `Authorization: Bearer <key>` header

### Discovery
```http
GET /.well-known/oauth-authorization-server
```

Returns OAuth endpoints (main hub only).

### Tool Invocation

MCP clients use the MCP protocol (SSE transport) to:
1. Connect to the server
2. List available tools
3. Invoke tools with arguments
4. Receive structured responses

See [MCP documentation](https://modelcontextprotocol.io) for protocol details.

---

## Error Responses

All APIs use consistent error format:

```json
{
  "error": "Error message",
  "detail": "Additional context (optional)"
}
```

**HTTP Status Codes:**
- `200` - Success
- `400` - Bad request (invalid input)
- `401` - Unauthorized (missing/invalid auth)
- `404` - Not found
- `500` - Internal server error

---

## Rate Limiting

Currently no rate limiting is enforced. Future versions may implement limits on:
- Agent API requests per minute
- MCP tool invocations per minute
- Supervisor mutations per hour
