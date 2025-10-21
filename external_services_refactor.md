# Luna External Services & Addon Store - Complete Specification

---

## Overview

**External Services** are infrastructure programs (Postgres, Redis, Tailscale, Grocy, etc.) that run independently of Luna, managed through shell commands.

**Addon Store** is a unified marketplace for both extensions (Python code) and external services (infrastructure), providing a single discovery and installation experience.

---

## Part 1: External Services

---

## Directory Structure

```
/opt/luna/luna-repo/
├── external_services/              (service definitions + user data)
│   ├── postgres/
│   │   ├── service.json            (service definition - keep)
│   │   ├── config.json             (user's config - delete on uninstall)
│   │   └── data/                   (volumes - delete on uninstall)
│   ├── redis/
│   │   ├── service.json
│   │   ├── config.json
│   │   └── data/
│   └── tailscale/
│       └── service.json
│
├── .luna/                          (git-ignored, runtime data)
│   ├── logs/                       (all external service logs)
│   │   ├── postgres.log
│   │   ├── redis.log
│   │   └── tailscale.log
│   └── external_services.json      (registry of installed services)
```

---

## Service Definition (service.json)

**Location**: `external_services/{name}/service.json`

**Structure**:

```json
{
  "name": "postgres",
  "display_name": "PostgreSQL",
  "description": "Relational database for structured data",
  "category": "database",
  
  "install_cmd": "bash external_services/postgres/install.sh {config_file}",
  "uninstall_cmd": "bash external_services/postgres/uninstall.sh {config_file}",
  "start_cmd": "docker start luna_postgres",
  "stop_cmd": "docker stop luna_postgres",
  "restart_cmd": "docker restart luna_postgres",
  
  "health_check_cmd": "docker ps --filter name=luna_postgres --format '{{.Status}}'",
  "health_check_expected": "Up",
  
  "enable_startup_cmd": "docker update --restart=unless-stopped luna_postgres",
  "disable_startup_cmd": "docker update --restart=no luna_postgres",
  
  "required_vars": [
    "DATABASE_URL",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD"
  ],
  
  "provides_vars": [
    "DATABASE_URL",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB"
  ]
}
```

**Field Descriptions**:

- `name`: Unique identifier
- `display_name`: Human-readable name for UI
- `description`: Short description for store listing
- `category`: For filtering in addon store
- `install_cmd`: Command to run installation (receives config file path)
- `uninstall_cmd`: Command to clean up service
- `start_cmd`: Command to start service
- `stop_cmd`: Command to stop service
- `restart_cmd`: Command to restart service
- `health_check_cmd`: Command to check if running
- `health_check_expected`: Substring to look for in health check output
- `enable_startup_cmd`: Command to enable auto-start on boot
- `disable_startup_cmd`: Command to disable auto-start
- `required_vars`: Variables user must configure (shown in install form)
- `provides_vars`: Variables this service makes available (display only, for UI info)

**Optional Fields**:

```json
{
  "working_dir": "/opt/luna/luna-repo",
  "requires_sudo": false,
  "install_timeout": 120
}
```

---

## Configuration Form (config-form.json)

**Location**: `external_services/{name}/config-form.json`

**Purpose**: Defines form fields shown during installation

```json
{
  "fields": [
    {
      "name": "database",
      "label": "Database Name",
      "type": "text",
      "default": "luna",
      "required": true,
      "help": "Name of the database to create"
    },
    {
      "name": "user",
      "label": "Username",
      "type": "text",
      "default": "luna_user",
      "required": true
    },
    {
      "name": "password",
      "label": "Password",
      "type": "password",
      "default": "",
      "required": true,
      "help": "Strong password for database access"
    },
    {
      "name": "port",
      "label": "Port",
      "type": "number",
      "default": 5432,
      "required": true
    }
  ]
}
```

**Field Types**: text, password, number, checkbox, select

**Attributes**:
- `name`: Key in config.json
- `label`: Display label
- `type`: Input type
- `default`: Default value
- `required`: Whether field is mandatory
- `help`: Optional help text
- `options`: Array of options (for select type)

---

## Installation Flow

### User Journey

1. User opens Addon Store
2. Clicks "Install" on PostgreSQL external service
3. **Modal shows configuration form** (from config-form.json)
4. User fills fields or accepts defaults
5. Reviews values
6. **Clicks "Start Installation"**
7. Frontend calls POST /api/external-services/{name}/install with configuration
8. Backend executes install_cmd with config file path
9. **Install script runs** (max 120 seconds from install_timeout):
   - Creates `external_services/{name}/` directory
   - Saves user config to `external_services/{name}/config.json`
   - Renders any templates using config values
   - Runs docker/systemctl commands to start service
   - Redirects logs to `.luna/logs/{name}.log`
10. **After install_cmd completes**:
    - Backend adds service to registry with installed=true
    - Backend adds service to state.json
    - Frontend shows success
    - Configuration displayed on Infrastructure page
    - User can manually copy values to .env if needed
    - Service appears on Infrastructure page
11. If **install script fails** (non-zero exit code):
    - Backend still marks as installed in registry
    - Status will show as unhealthy after first health check
    - User can troubleshoot via logs or uninstall and retry

### Configuration Storage

**Location**: `external_services/{name}/config.json`

User's installation configuration saved permanently:

```json
{
  "database": "luna",
  "user": "luna_user",
  "password": "secure_password_here",
  "port": 5432,
  "installed_at": "2025-10-19T12:00:00Z"
}
```

This config is:
- Passed to install script as `{config_file}` argument
- Displayed on Infrastructure page for reference
- Used for uninstall operations
- Available for user to copy values to .env

### No Automatic .env Linking

**Important**: Install script does NOT automatically add variables to .env file.

**Instead**: Configuration values displayed in UI for user to manually copy to .env if their extensions need them.

**Why**: Keeps it simple, explicit, and gives user control over their environment file.

---

## Logging

### Log Location

All external service logs stored in: `.luna/logs/`

**Log files**: `.luna/logs/{service_name}.log`

Examples:
- `.luna/logs/postgres.log`
- `.luna/logs/redis.log`
- `.luna/logs/tailscale.log`

### Log Capture

**During installation**:
Install script should redirect output to log file:
```bash
#!/bin/bash
# In install.sh
LOG_FILE=".luna/logs/postgres.log"
mkdir -p .luna/logs

{
  echo "=== Installation started at $(date) ==="
  # Installation commands here
  echo "=== Installation completed at $(date) ==="
} >> "$LOG_FILE" 2>&1
```

**During runtime**:
- Docker containers: Configure Docker logging to append to log file
- System services: Configure systemd to journal to log file
- Services should append, not overwrite

**Log rotation**:
- Not implemented in MVP
- Future enhancement: rotate logs at 10MB or weekly

---

## External Services Registry

**Location**: `.luna/external_services.json` (git-ignored)

```json
{
  "postgres": {
    "installed": true,
    "installed_at": "2025-10-19T12:00:00Z",
    "enabled": true,
    "status": "running",
    "config_path": ".luna/external_services/postgres/config.json",
    "log_path": ".luna/logs/postgres.log",
    "last_health_check": "2025-10-19T14:30:00Z"
  },
  "redis": {
    "installed": true,
    "installed_at": "2025-10-19T13:00:00Z",
    "enabled": false,
    "status": "stopped",
    "config_path": ".luna/external_services/redis/config.json",
    "log_path": ".luna/logs/redis.log",
    "last_health_check": "2025-10-19T14:30:00Z"
  }
}
```

**Status Values**: "running", "stopped", "unhealthy", "unknown"

**Fields**:
- `installed`: Always true for entries in registry
- `installed_at`: ISO timestamp of installation
- `enabled`: Whether auto-start on boot is enabled
- `status`: Current running status
- `config_path`: Path to saved configuration
- `log_path`: Path to log file
- `last_health_check`: ISO timestamp of last health check

---

## Supervisor Integration

### On Startup

Supervisor does **NOT** start external services. Only:

1. Loads `.luna/external_services.json`
2. Adds installed services to monitoring list
3. Begins health check loop

Services start via:
- Docker restart policy (if enabled=true)
- Manual start button in UI

### Health Monitoring

Every 30 seconds:

1. For each installed service:
   - Execute health_check_cmd
   - Capture stdout
   - Check if health_check_expected substring in output
   - Update status:
     - "running" if expected string found
     - "stopped" if expected string not found
     - "unhealthy" if command fails
     - "unknown" if timeout
   - Update last_health_check timestamp
   - Write to state.json

2. **No auto-restart** - just monitoring and reporting

### State Tracking

**state.json** includes:

```json
{
  "services": {...},
  "external_services": {
    "postgres": {
      "status": "running",
      "last_check": "2025-10-19T14:30:00Z"
    },
    "redis": {
      "status": "stopped",
      "last_check": "2025-10-19T14:30:00Z"
    }
  }
}
```

---

## Management Operations

### Start Service

**Trigger**: User clicks "Start" button in UI

**Flow**:
1. Frontend calls POST /api/external-services/{name}/start
2. Backend loads service.json
3. Executes start_cmd
4. Waits up to 10 seconds
5. Runs health check
6. Updates registry and state
7. Returns new status to frontend

### Stop Service

**Trigger**: User clicks "Stop" button in UI

**Flow**:
1. Frontend calls POST /api/external-services/{name}/stop
2. Backend loads service.json
3. Executes stop_cmd
4. Updates status to "stopped"
5. Updates registry and state
6. Returns to frontend

### Restart Service

**Trigger**: User clicks "Restart" button in UI

**Flow**:
1. Frontend calls POST /api/external-services/{name}/restart
2. Backend executes stop_cmd
3. **Wait 5 seconds**
4. Backend executes start_cmd
5. Waits up to 10 seconds
6. Runs health check
7. Updates status
8. Returns to frontend

### Enable/Disable Auto-Start

**Enable** (start on system boot):
1. User toggles "Enabled" checkbox on
2. Frontend calls POST /api/external-services/{name}/enable
3. Backend executes enable_startup_cmd
4. Updates registry: enabled=true
5. Service will now auto-start on system boot

**Disable** (don't start on boot):
1. User toggles "Enabled" checkbox off
2. Frontend calls POST /api/external-services/{name}/disable
3. Backend executes disable_startup_cmd
4. Updates registry: enabled=false
5. Service won't auto-start on system boot

**Note**: Enable/disable only controls auto-start. Service can be manually started/stopped regardless of enabled state.

### Uninstall Service

**Trigger**: User clicks "Delete" button on Infrastructure page, confirms in modal

**Flow**:
1. Frontend calls POST /api/external-services/{name}/uninstall
2. Backend executes stop_cmd first (ensure stopped)
3. Backend executes uninstall_cmd with config_file path
4. Uninstall script:
   - Removes Docker container and images
   - Removes data volumes (or preserves based on user choice in modal)
   - Cleans up any created files
5. Backend removes service from registry (.luna/external_services.json)
6. Backend removes service from state.json
7. Backend optionally removes log file (.luna/logs/{name}.log)
8. Frontend removes service from UI

---

## API Endpoints

### List Available External Services
```
GET /api/external-services/available
```
Returns array of all service definitions from external_services/ directory

Response:
```json
[
  {
    "name": "postgres",
    "display_name": "PostgreSQL",
    "description": "...",
    "category": "database",
    "installed": false
  },
  ...
]
```

### List Installed External Services
```
GET /api/external-services/installed
```
Returns contents of .luna/external_services.json with current statuses

Response:
```json
{
  "postgres": {
    "installed": true,
    "status": "running",
    "enabled": true,
    ...
  }
}
```

### Get Service Details
```
GET /api/external-services/{name}
```
Returns service.json + config-form.json + installation status + saved config

Response:
```json
{
  "definition": {...},
  "form": {...},
  "installed": true,
  "config": {...}
}
```

### Install Service
```
POST /api/external-services/{name}/install
Body: {
  "config": {
    "database": "luna",
    "user": "luna_user",
    "password": "secure_password",
    "port": 5432
  }
}
```
1. Validates required fields from config-form.json
2. Creates `external_services/{name}/` directory
3. Saves config to `config.json`
4. Executes install_cmd with config_file path
5. Waits up to install_timeout seconds
6. After completion, adds to registry as installed=true
7. Returns success

Response:
```json
{
  "success": true,
  "config": {...}
}
```

### Uninstall Service
```
POST /api/external-services/{name}/uninstall
Body: {
  "remove_data": true
}
```
Executes uninstall process and removes from registry

Response:
```json
{
  "success": true
}
```

### Start Service
```
POST /api/external-services/{name}/start
```
Executes start_cmd and updates status

Response:
```json
{
  "status": "running"
}
```

### Stop Service
```
POST /api/external-services/{name}/stop
```
Executes stop_cmd and updates status

Response:
```json
{
  "status": "stopped"
}
```

### Restart Service
```
POST /api/external-services/{name}/restart
```
Executes stop_cmd, waits 5 seconds, executes start_cmd

Response:
```json
{
  "status": "running"
}
```

### Enable Auto-Start
```
POST /api/external-services/{name}/enable
```
Executes enable_startup_cmd and updates registry

Response:
```json
{
  "enabled": true
}
```

### Disable Auto-Start
```
POST /api/external-services/{name}/disable
```
Executes disable_startup_cmd and updates registry

Response:
```json
{
  "enabled": false
}
```

### Get Current Status
```
GET /api/external-services/{name}/status
```
Returns current status from state.json and registry

Response:
```json
{
  "status": "running",
  "enabled": true,
  "last_check": "2025-10-19T14:30:00Z"
}
```

### Get Service Logs
```
GET /api/external-services/{name}/logs?lines=100
```
Returns last N lines from `.luna/logs/{name}.log`

Response:
```json
{
  "logs": "log content here...",
  "path": ".luna/logs/postgres.log"
}
```

---

## Command Execution Details

### Working Directory

Commands executed from repository root (`/opt/luna/luna-repo`) unless working_dir specified in service.json.

### Environment Variables

Commands inherit Luna's environment plus any specified in service.json `env` field.

### Output Handling

- stdout and stderr captured
- All output logged to supervisor logs
- Install script should additionally log to `.luna/logs/{name}.log`
- Health check output parsed for expected string

### Timeouts

- Install: From install_timeout field (default 120 seconds)
- Start/stop/restart: 30 seconds
- Health checks: 10 seconds
- If timeout: Log error, continue execution

### Error Handling

**If install_cmd fails** (non-zero exit code):
1. Capture exit code and output
2. Log to supervisor logs and service log file
3. Still mark service as installed in registry
4. Status will show as unhealthy on first health check
5. Return error to frontend but installation marked complete
6. User can view logs to troubleshoot
7. User can uninstall and retry with different config

**If start/stop/restart fails**:
1. Capture error
2. Log error
3. Update status to unhealthy or stopped
4. Return error to frontend
5. No automatic retry

---

## Docker vs Direct Commands

**For single-container services**: Use direct `docker` commands, not docker-compose

**Example - Simple approach**:
```json
{
  "start_cmd": "docker start luna_postgres",
  "stop_cmd": "docker stop luna_postgres",
  "restart_cmd": "docker restart luna_postgres"
}
```

**Example - Full docker run in install script**:
```bash
#!/bin/bash
# install.sh
CONFIG_FILE=$1
LOG_FILE=".luna/logs/postgres.log"

# Parse config
DATABASE=$(jq -r '.database' "$CONFIG_FILE")
USER=$(jq -r '.user' "$CONFIG_FILE")
PASSWORD=$(jq -r '.password' "$CONFIG_FILE")
PORT=$(jq -r '.port' "$CONFIG_FILE")

# Log to file
mkdir -p .luna/logs
{
  echo "=== PostgreSQL Installation $(date) ==="
  
  docker run -d \
    --name luna_postgres \
    --restart unless-stopped \
    -p $PORT:5432 \
    -e POSTGRES_DB=$DATABASE \
    -e POSTGRES_USER=$USER \
    -e POSTGRES_PASSWORD=$PASSWORD \
    -v $(pwd)/external_services/postgres/data:/var/lib/postgresql/data \
    postgres:16-alpine
    
  echo "=== Installation complete $(date) ==="
} >> "$LOG_FILE" 2>&1
```

**Docker Compose only needed if**:
- Multiple containers that need to communicate
- Complex networking setup
- Want docker-compose.yml for documentation

Otherwise, direct `docker` commands are simpler and sufficient.

---

## Hub UI - Infrastructure Page

**Route**: `/infrastructure`

**Purpose**: Manage installed external services only (not browse available ones)

### Page Layout

**Single Section: Installed Services**

Grid of cards showing each installed service:

```
┌────────────────────────────────────────────┐
│  Infrastructure                             │
├────────────────────────────────────────────┤
│                                            │
│  External Services                         │
│  ────────────────────────                  │
│                                            │
│  ┌──────────────────┐  ┌──────────────┐   │
│  │ PostgreSQL       │  │ Redis        │   │
│  │ ● Running        │  │ ○ Stopped    │   │
│  │ Port: 5432       │  │ Port: 6379   │   │
│  │                  │  │              │   │
│  │ [◉] Enabled      │  │ [○] Enabled  │   │
│  │                  │  │              │   │
│  │ [Stop] [Restart] │  │ [Start]      │   │
│  │ [View Logs]      │  │ [View Logs]  │   │
│  │ [Delete]         │  │ [Delete]     │   │
│  │                  │  │              │   │
│  │ [▼] Configuration│  │ Configuration│   │
│  └──────────────────┘  └──────────────┘   │
│                                            │
│  No available services shown here          │
│  Visit Addon Store to install more         │
│                                            │
└────────────────────────────────────────────┘
```

**Card Contents**:
- Service name and icon
- Status indicator:
  - ● Green = running
  - ○ Gray = stopped
  - ⚠️ Yellow = unhealthy
  - ? Gray = unknown
- Port (if configured)
- **Enable/disable toggle** (controls auto-start on boot)
- **Control buttons**:
  - Start (if stopped)
  - Stop (if running)
  - Restart (if running)
  - View Logs
  - Delete
- **Configuration section** (expandable):
  - Shows values from config.json
  - "Copy to .env" helper text
  - Copy to clipboard button

**If no services installed**:
Show empty state message with link to Addon Store

**To install new services**: User must go to Addon Store

### Service Card Details

**Status Indicators**:
- ● Green dot + "Running" = healthy
- ○ Gray dot + "Stopped" = not running
- ⚠️ Yellow dot + "Unhealthy" = running but health check failing
- ? Gray dot + "Unknown" = health check error or timeout

**Enable/Disable Toggle**:
- Checked = Auto-starts on system boot
- Unchecked = Won't auto-start
- Changes take effect immediately (calls enable/disable API)

**Control Buttons**:
- Shown based on current status
- Disabled during operation (show spinner)
- Re-enabled after operation completes

**Configuration Display**:
Expandable section showing:
```
Configuration
─────────────
database: luna
user: luna_user
password: ••••••••••••
port: 5432

These values can be added to your .env file
if extensions require them.

[Copy to Clipboard]
```

**View Logs Button**:
Opens modal showing last 100 lines from `.luna/logs/{name}.log`

**Delete Button**:
Opens confirmation modal:
```
┌────────────────────────────────────┐
│  Delete PostgreSQL?                │
├────────────────────────────────────┤
│                                    │
│  This will stop and remove the     │
│  service.                          │
│                                    │
│  [✓] Also delete data volumes      │
│                                    │
│  [Cancel]  [Delete]                │
└────────────────────────────────────┘
```

### Top Banner Notification

When enabled service is not running:

```
⚠️ PostgreSQL is enabled but not running [Start Service] [Dismiss]
```

Shows at top of all Hub UI pages when:
- Service has enabled=true in registry
- Status is "stopped" or "unhealthy"

Clicking "Start Service" immediately triggers start operation.

Clicking "Dismiss" hides banner until next page load.

---

## Example Service Definitions

### PostgreSQL (Docker, single container)

**service.json**:
```json
{
  "name": "postgres",
  "display_name": "PostgreSQL",
  "category": "database",
  "description": "Relational database for structured data",
  "install_cmd": "bash external_services/postgres/install.sh {config_file}",
  "uninstall_cmd": "bash external_services/postgres/uninstall.sh {config_file}",
  "start_cmd": "docker start luna_postgres",
  "stop_cmd": "docker stop luna_postgres",
  "restart_cmd": "docker restart luna_postgres",
  "health_check_cmd": "docker ps --filter name=luna_postgres --format '{{.Status}}'",
  "health_check_expected": "Up",
  "enable_startup_cmd": "docker update --restart=unless-stopped luna_postgres",
  "disable_startup_cmd": "docker update --restart=no luna_postgres",
  "install_timeout": 120,
  "required_vars": ["DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD"],
  "provides_vars": ["DATABASE_URL", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
}
```

**config-form.json**:
```json
{
  "fields": [
    {
      "name": "database",
      "label": "Database Name",
      "type": "text",
      "default": "luna",
      "required": true
    },
    {
      "name": "user",
      "label": "Username",
      "type": "text",
      "default": "luna_user",
      "required": true
    },
    {
      "name": "password",
      "label": "Password",
      "type": "password",
      "default": "",
      "required": true
    },
    {
      "name": "port",
      "label": "Port",
      "type": "number",
      "default": 5432,
      "required": true
    }
  ]
}
```

### Tailscale (System service)

**service.json**:
```json
{
  "name": "tailscale",
  "display_name": "Tailscale VPN",
  "category": "network",
  "description": "Zero-config VPN for secure remote access",
  "requires_sudo": true,
  "install_cmd": "bash external_services/tailscale/install.sh {config_file}",
  "uninstall_cmd": "sudo apt remove tailscale -y",
  "start_cmd": "sudo systemctl start tailscaled",
  "stop_cmd": "sudo systemctl stop tailscaled",
  "restart_cmd": "sudo systemctl restart tailscaled",
  "health_check_cmd": "systemctl is-active tailscaled",
  "health_check_expected": "active",
  "enable_startup_cmd": "sudo systemctl enable tailscaled",
  "disable_startup_cmd": "sudo systemctl disable tailscaled",
  "install_timeout": 60,
  "required_vars": [],
  "provides_vars": []
}
```

**config-form.json**:
```json
{
  "fields": []
}
```

### Redis (Docker, single container)

**service.json**:
```json
{
  "name": "redis",
  "display_name": "Redis",
  "category": "cache",
  "description": "In-memory data store for caching",
  "install_cmd": "bash external_services/redis/install.sh {config_file}",
  "uninstall_cmd": "bash external_services/redis/uninstall.sh {config_file}",
  "start_cmd": "docker start luna_redis",
  "stop_cmd": "docker stop luna_redis",
  "restart_cmd": "docker restart luna_redis",
  "health_check_cmd": "docker exec luna_redis redis-cli ping",
  "health_check_expected": "PONG",
  "enable_startup_cmd": "docker update --restart=unless-stopped luna_redis",
  "disable_startup_cmd": "docker update --restart=no luna_redis",
  "install_timeout": 90,
  "required_vars": ["REDIS_URL"],
  "provides_vars": ["REDIS_URL", "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"]
}
```

### Grocy (Docker with web UI)

**service.json**:
```json
{
  "name": "grocy",
  "display_name": "Grocy",
  "category": "application",
  "description": "Grocery and household management",
  "install_cmd": "bash external_services/grocy/install.sh {config_file}",
  "uninstall_cmd": "bash external_services/grocy/uninstall.sh {config_file}",
  "start_cmd": "docker start luna_grocy",
  "stop_cmd": "docker stop luna_grocy",
  "restart_cmd": "docker restart luna_grocy",
  "health_check_cmd": "curl -f http://localhost:{port}/api/system/info",
  "health_check_expected": "grocy",
  "enable_startup_cmd": "docker update --restart=unless-stopped luna_grocy",
  "disable_startup_cmd": "docker update --restart=no luna_grocy",
  "install_timeout": 180,
  "required_vars": ["GROCY_URL"],
  "provides_vars": ["GROCY_URL"]
}
```

---

## Part 2: Addon Store Integration

---

## Concept

**Addon Store** is the unified marketplace for:
- **Extensions**: Python code that adds tools, services, UIs to Luna
- **External Services**: Infrastructure like databases, applications

Single discovery and browsing experience. Different installation flows based on type.

---

## Registry Structure

**Location**: `https://raw.githubusercontent.com/luna-addons/luna-addons/main/registry.json`

**Monorepo**: `luna-addons` replaces old `luna-extensions` repo

**Structure**:
```
luna-addons/
├── registry.json
├── extensions/              (embedded extensions)
│   ├── notes/
│   ├── todos/
│   ├── calendar/
│   └── weather/
└── external_services/       (bundled external services)
    ├── postgres/
    ├── redis/
    ├── mongodb/
    └── grocy/
```

**Registry Schema**:

```json
{
  "version": "10-19-25",
  "last_updated": "2025-10-19T12:00:00Z",
  
  "addons": [
    {
      "id": "notes",
      "name": "Notes",
      "type": "extension",
      "category": "productivity",
      "description": "Simple note-taking with tags and search",
      "author": "Luna Team",
      "version": "10-17-25",
      "source": {
        "type": "embedded",
        "path": "extensions/notes"
      },
      "has_ui": false,
      "tool_count": 3,
      "service_count": 0,
      "required_secrets": ["OPENAI_API_KEY"],
      "tags": ["notes", "productivity"]
    },
    {
      "id": "automation_memory",
      "name": "Automation Memory",
      "type": "extension",
      "category": "automation",
      "description": "Task automation and memory management",
      "author": "Luna Team",
      "version": "10-17-25",
      "source": {
        "type": "embedded",
        "path": "extensions/automation_memory"
      },
      "has_ui": true,
      "tool_count": 8,
      "service_count": 1,
      "required_secrets": ["DATABASE_URL"],
      "dependencies": ["postgres"],
      "tags": ["automation", "memory", "tasks"]
    },
    {
      "id": "postgres",
      "name": "PostgreSQL",
      "type": "external_service",
      "category": "database",
      "description": "Relational database for structured data",
      "author": "PostgreSQL Community",
      "version": "16-alpine",
      "source": {
        "type": "embedded",
        "path": "external_services/postgres"
      },
      "provides_vars": [
        "DATABASE_URL",
        "POSTGRES_HOST",
        "POSTGRES_PORT"
      ],
      "tags": ["database", "sql", "infrastructure"]
    },
    {
      "id": "grocy",
      "name": "Grocy",
      "type": "external_service",
      "category": "application",
      "description": "Grocery and household management",
      "author": "Grocy Community",
      "version": "4.0",
      "source": {
        "type": "embedded",
        "path": "external_services/grocy"
      },
      "has_ui": true,
      "provides_vars": ["GROCY_URL"],
      "tags": ["household", "groceries", "inventory"]
    },
    {
      "id": "github_sync",
      "name": "GitHub Sync",
      "type": "extension",
      "category": "development",
      "description": "Sync GitHub issues, PRs, and repositories",
      "author": "Luna Team",
      "version": "10-15-25",
      "source": {
        "type": "external",
        "repo": "github:luna-extensions/github-sync"
      },
      "has_ui": true,
      "tool_count": 12,
      "service_count": 1,
      "required_secrets": ["GITHUB_TOKEN"],
      "tags": ["github", "development", "sync"]
    }
  ],
  
  "categories": [
    {"id": "productivity", "name": "Productivity", "icon": "📝"},
    {"id": "development", "name": "Development", "icon": "💻"},
    {"id": "automation", "name": "Automation", "icon": "🤖"},
    {"id": "database", "name": "Databases", "icon": "💾"},
    {"id": "application", "name": "Applications", "icon": "📱"},
    {"id": "network", "name": "Network", "icon": "🌐"},
    {"id": "communication", "name": "Communication", "icon": "💬"}
  ]
}
```

---

## Registry Schema Fields

### Common Fields (Both Types)

- `id` (string, required): Unique identifier
- `name` (string, required): Display name
- `type` (string, required): "extension" or "external_service"
- `category` (string, required): From categories list
- `description` (string, required): Short description for cards
- `author` (string, required): Creator name
- `version` (string, required): Current version (MM-DD-YY format)
- `source` (object, required): Where to get the addon
  - `type`: "embedded" or "external"
  - `path`: If embedded, path within luna-addons repo
  - `repo`: If external, GitHub URL format
- `tags` (array, required): Searchable keywords

### Extension-Specific Fields

- `has_ui` (boolean): Whether extension has a UI component
- `tool_count` (number): Number of tools provided
- `service_count` (number): Number of background services
- `required_secrets` (array): .env variables needed
- `dependencies` (array): External service IDs this extension requires

### External Service-Specific Fields

- `provides_vars` (array): Variables this service provides (display only)
- `has_ui` (boolean): If service has web UI (like Grocy)

---

## Addon Store UI

**Route**: `/store`

**Page Title**: "Addon Store"

### Layout

**Single unified grid** showing both extensions and external services together:

```
┌────────────────────────────────────────────┐
│  Addon Store                    [Search]   │
├────────────────────────────────────────────┤
│                                            │
│  [All] Extensions  Services                │
│  [All] Productivity  Development  Database │
│                                            │
│  ┌──────────────┐  ┌──────────────┐       │
│  │ 📝 Notes     │  │ 💾 PostgreSQL│       │
│  │ Extension    │  │ Service      │       │
│  │ ──────────── │  │ ──────────── │       │
│  │ Note-taking  │  │ Database for │       │
│  │ with search  │  │ extensions   │       │
│  │              │  │              │       │
│  │ 3 tools      │  │ Provides:    │       │
│  │              │  │ • DATABASE_  │       │
│  │ Requires:    │  │   URL        │       │
│  │ • OPENAI_*   │  │ • POSTGRES_* │       │
│  │              │  │              │       │
│  │ [Install]    │  │ [Install]    │       │
│  └──────────────┘  └──────────────┘       │
│                                            │
│  ┌──────────────┐  ┌──────────────┐       │
│  │ 🤖 Automation│  │ 📱 Grocy     │       │
│  │ Memory       │  │ Service      │       │
│  │ Extension    │  │ ──────────── │       │
│  │ ──────────── │  │ Household    │       │
│  │ Task flows & │  │ management   │       │
│  │ scheduling   │  │              │       │
│  │              │  │ Has web UI   │       │
│  │ 8 tools      │  │              │       │
│  │ 1 service    │  │ Provides:    │       │
│  │              │  │ • GROCY_URL  │       │
│  │ Depends on:  │  │              │       │
│  │ • PostgreSQL │  │ [Install]    │       │
│  │              │  │              │       │
│  │ [Install]    │  │              │       │
│  └──────────────┘  └──────────────┘       │
│                                            │
└────────────────────────────────────────────┘
```

### Card Visual Distinctions

**Extension Cards**:
- "Extension" badge (blue background)
- Shows tool count
- Shows service count (if > 0)
- Shows "Has UI" indicator if has_ui=true
- Lists required secrets
- Lists dependencies (other addons needed)
- Install button

**External Service Cards**:
- "Service" badge (green background)
- Shows "Provides: X variables" (from provides_vars array)
- Shows "Has web UI" if has_ui=true
- Install button

**Installed Indicator**:
- If already installed: Show "✓ Installed" instead of "Install" button
- Gray out install button
- Add "Manage" link that navigates to:
  - Extensions page if type=extension
  - Infrastructure page if type=external_service

### Filters

**Type Filter** (buttons at top):
- All (default, shows both types)
- Extensions (shows only type=extension)
- Services (shows only type=external_service)

**Category Filter** (buttons below type):
- All (default)
- Productivity
- Development
- Automation
- Databases
- Applications
- Network
- Communication

**Additional Filters** (checkboxes on side or dropdown):
- Has UI
- No dependencies
- Installed only
- Free (no API keys required - check required_secrets empty)

**All filters combine** with AND logic.

### Search

**Search bar** at top right

**Searches across**:
- Addon name
- Description
- Tags
- Dependencies (for extensions)
- Provides_vars (for services)

**Example**: Search "database" returns:
- PostgreSQL service (category=database)
- MongoDB service (category=database)
- Automation Memory extension (dependencies includes postgres)

**Debounced**: 300ms delay after typing

### Sort Options

**Sort by** (dropdown):
- Name (A-Z)
- Name (Z-A)
- Recently Added
- Category

---

## Installation Flows

### Installing External Service from Store

1. User browses Addon Store
2. Clicks "Install" on external service (e.g., PostgreSQL)
3. **Modal opens** with configuration form from config-form.json
4. User fills fields or accepts defaults
5. Clicks "Start Installation"
6. Frontend calls POST /api/external-services/{name}/install with config
7. **Installation happens immediately** (no queue, no restart)
8. Progress indicator shown (max install_timeout seconds)
9. After completion:
   - Success message shown
   - Configuration displayed for manual .env copying
   - Modal closes
   - Service now shows as "✓ Installed" in store
   - Service appears on Infrastructure page
10. User can go to Infrastructure page to manage service

**Installation flow** detailed in Part 1: External Services section.

### Extension Installation

Extension installation not detailed in this specification. Refer to main Luna specification for extension installation process via queue system.

**Note**: Users can install extensions even if dependencies are not satisfied. No blocking or warnings about missing dependencies.

---

## Detail Modals

### Extension Detail Modal

When user clicks extension card (not install button):

**Tabs**:
- **Overview**: Full description, author, version, tags, screenshots (if available)
- **Requirements**: Lists required_secrets and dependencies with current status
- **Tools**: List of tools this extension provides with descriptions
- **Services**: Background services info (if service_count > 0)

**Footer**:
- "Install" button (primary)
- "View Source" link (if source repo available)
- "Close" button

### External Service Detail Modal

When user clicks external service card (not install button):

**Tabs**:
- **Overview**: Full description, author, version, what it does
- **Configuration**: Preview of config form fields
- **Provides**: List of environment variables from provides_vars array
- **Documentation**: Links to official docs (if available)

**Footer**:
- "Install" button (primary)
- "View Source" link
- "Close" button

---

## API Endpoints

### Get Addon Registry
```
GET /api/addons/registry
```
Returns complete registry.json with all addons

### Filter Addons
```
GET /api/addons?type=extension
GET /api/addons?type=external_service
GET /api/addons?category=database
GET /api/addons?has_ui=true
GET /api/addons?installed=true
```
Returns filtered subset of addons

### Get Addon Details
```
GET /api/addons/{id}
```
Returns single addon with full details including installation status

### Check Dependencies
```
GET /api/addons/{id}/dependencies
```
Returns dependency information

Response:
```json
{
  "required": ["postgres"],
  "satisfied": [
    {
      "id": "postgres",
      "name": "PostgreSQL",
      "installed": true
    }
  ],
  "missing": []
}
```

### Install Addon
```
POST /api/addons/install
Body: {
  "id": "postgres",
  "type": "external_service",
  "config": {...}
}
```

**Behavior**:
- If type=extension: Routes to extension installation (queue system)
- If type=external_service: Routes to POST /api/external-services/{name}/install

Response for extension:
```json
{
  "success": true,
  "queued": true
}
```

Response for external service:
```json
{
  "success": true,
  "immediate": true,
  "config": {...}
}
```

---

## Search and Discovery

### Unified Search

Single search box searches across all addons (both types).

**Matching logic**:
- Searches name (case-insensitive)
- Searches description (case-insensitive)
- Searches tags array
- For extensions: searches dependencies array
- For services: searches provides_vars array

**Results display**: Mixed grid showing both types with appropriate badges

**Ranking**: Exact name matches first, then description matches, then tag matches

### Smart Suggestions

**Future enhancement** (not MVP):
- When viewing extension with dependencies, suggest those services
- When viewing service, show extensions that use it
- "People who installed X also installed Y"

---

## Complete User Journey Example

**Scenario**: User wants to use Automation Memory extension

1. User opens Addon Store (`/store` route)
2. Searches "automation"
3. Sees "Automation Memory" extension card
4. Clicks card to view details
5. Detail modal shows:
   - Description of extension
   - Dependencies: PostgreSQL
   - Required secrets: DATABASE_URL
6. User notes PostgreSQL dependency
7. Clicks "Close" on modal
8. Searches "postgres" or filters by Database category
9. Sees "PostgreSQL" service card
10. Clicks "Install" on PostgreSQL
11. Configuration modal opens:
    - Database name: luna (default)
    - Username: luna_user (default)
    - Password: (empty, user must enter)
    - Port: 5432 (default)
12. User enters strong password
13. Clicks "Start Installation"
14. Progress indicator shown (max 120 seconds)
15. Installation completes successfully
16. Success message shown with configuration:
    ```
    PostgreSQL installed successfully!
    
    Configuration:
    DATABASE_URL=postgresql://luna_user:password@localhost:5432/luna
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_USER=luna_user
    POSTGRES_PASSWORD=••••••••
    POSTGRES_DB=luna
    
    [Copy to Clipboard]
    
    You can add these to your .env file if needed by extensions.
    ```
17. User clicks "Copy to Clipboard"
18. User navigates to Secrets tab
19. User manually adds DATABASE_URL to .env via Key Manager
20. User returns to Addon Store
21. Clicks "Install" on Automation Memory extension
22. Extension added to queue (standard extension flow)
23. User goes to Queue tab
24. Saves to queue
25. Clicks "Restart & Apply"
26. System restarts
27. Automation Memory installed and working
28. Automation Memory can connect to PostgreSQL via DATABASE_URL

---

## Key Principles

1. **Unified Discovery**: Single Addon Store for all addons
2. **Clear Type Distinction**: Visual badges and different card layouts
3. **Different Installation Flows**:
   - Extensions: Queue system, requires restart
   - External services: Immediate install, no restart
4. **No Dependency Blocking**: Users can install extensions without dependencies
5. **Manual Configuration**: Users manually copy variables to .env
6. **Independence**: External services survive Luna restarts
7. **Command-Based**: All service operations via shell commands
8. **User Control**: All actions explicit via UI
9. **Logging**: All services log to `.luna/logs/`
10. **Simple Management**: Infrastructure page mirrors Extensions page UX

---

## Implementation Checklist

### Backend

**External Services**:
- [ ] Service discovery from external_services/ directory
- [ ] Registry management (.luna/external_services.json)
- [ ] Command execution with timeout and error handling
- [ ] Health check loop in supervisor (every 30 seconds)
- [ ] State tracking in state.json
- [ ] Log file management (.luna/logs/)
- [ ] API endpoints for all operations
- [ ] Config file interpolation for install commands

**Addon Store**:
- [ ] Fetch and cache registry.json
- [ ] Filter and search logic
- [ ] Dependency checking API
- [ ] Unified install endpoint routing

### Frontend

**Infrastructure Page**:
- [ ] Installed services grid
- [ ] Service cards with status
- [ ] Enable/disable toggle
- [ ] Start/stop/restart buttons
- [ ] Configuration display
- [ ] View logs modal
- [ ] Delete confirmation
- [ ] Top banner notification

**Addon Store**:
- [ ] Unified grid for both types
- [ ] Type and category filters
- [ ] Search functionality
- [ ] Extension cards (blue badge)
- [ ] External service cards (green badge)
- [ ] Install modals (different for each type)
- [ ] Detail modals
- [ ] Install status tracking

### Bundled Services

- [ ] PostgreSQL definition + install script
- [ ] Redis definition + install script
- [ ] Tailscale definition + install script
- [ ] Example docker commands vs scripts

### Documentation

- [ ] How to create external service definition
- [ ] Command format requirements
- [ ] Config form schema
- [ ] Install script best practices
- [ ] Logging requirements

---

This complete specification covers all aspects of external services and their integration into the unified Addon Store, providing a comprehensive guide for implementation.