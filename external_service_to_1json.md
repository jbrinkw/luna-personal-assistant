# External Service Upload - Single JSON File

You're absolutely right - let's simplify this!

---

## Current Problem

External services currently require multiple files:
- `service.json` (metadata)
- `config-form.json` (form fields)
- `install.sh` (bash script)
- `uninstall.sh` (bash script)

This makes them hard to share and upload.

---

## Better Solution: Single JSON File

**Merge everything into one file**: `service.json`

### New Unified Structure

```json
{
  "name": "postgres",
  "display_name": "PostgreSQL",
  "description": "Relational database for structured data",
  "category": "database",
  "author": "Luna Team",
  "version": "16-alpine",
  
  "config_form": {
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
  },
  
  "commands": {
    "install": "mkdir -p external_services/postgres/data .luna/logs && docker run -d --name luna_postgres --restart unless-stopped -p {{port}}:5432 -e POSTGRES_DB={{database}} -e POSTGRES_USER={{user}} -e POSTGRES_PASSWORD={{password}} -v $(pwd)/external_services/postgres/data:/var/lib/postgresql/data postgres:16-alpine >> .luna/logs/postgres.log 2>&1",
    
    "uninstall": "docker stop luna_postgres && docker rm luna_postgres",
    
    "start": "docker start luna_postgres",
    
    "stop": "docker stop luna_postgres",
    
    "restart": "docker restart luna_postgres",
    
    "health_check": "docker ps --filter name=luna_postgres --format '{{.Status}}'",
    
    "enable_startup": "docker update --restart=unless-stopped luna_postgres",
    
    "disable_startup": "docker update --restart=no luna_postgres"
  },
  
  "health_check_expected": "Up",
  "install_timeout": 120,
  "working_dir": "/opt/luna/luna-repo",
  
  "required_vars": ["DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD"],
  "provides_vars": ["DATABASE_URL", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
}
```

---

## Key Changes

### 1. Inline config_form
Instead of separate `config-form.json`, it's nested under `config_form` key.

### 2. Commands object
All commands in one place under `commands` key:
- `install` - Installation command
- `uninstall` - Cleanup command
- `start` - Start service
- `stop` - Stop service
- `restart` - Restart service
- `health_check` - Health check command
- `enable_startup` - Enable auto-start
- `disable_startup` - Disable auto-start

### 3. Template variables
Commands can use `{{variable}}` syntax for config values:
- `{{database}}` → Value from user's config
- `{{user}}` → Value from user's config
- `{{password}}` → Value from user's config
- `{{port}}` → Value from user's config

Backend replaces these when executing commands.

### 4. Multi-line commands
For complex installs, use JSON multi-line strings:

```json
{
  "commands": {
    "install": "mkdir -p external_services/postgres/data .luna/logs\nCONFIG_FILE={config_file}\nDATABASE=$(jq -r '.database' $CONFIG_FILE)\nUSER=$(jq -r '.user' $CONFIG_FILE)\nPASSWORD=$(jq -r '.password' $CONFIG_FILE)\nPORT=$(jq -r '.port' $CONFIG_FILE)\ndocker run -d --name luna_postgres --restart unless-stopped -p $PORT:5432 -e POSTGRES_DB=$DATABASE -e POSTGRES_USER=$USER -e POSTGRES_PASSWORD=$PASSWORD -v $(pwd)/external_services/postgres/data:/var/lib/postgresql/data postgres:16-alpine >> .luna/logs/postgres.log 2>&1"
  }
}
```

Or for really complex cases, commands can reference external scripts:
```json
{
  "commands": {
    "install": "bash external_services/postgres/install.sh {config_file}"
  }
}
```

---

## Upload Functionality

### Infrastructure Page Upload Button

Add upload button to Infrastructure page:

```
┌────────────────────────────────────────────┐
│  Infrastructure           [+ Upload Service]│
├────────────────────────────────────────────┤
│                                            │
│  Installed Services                        │
│  (service cards...)                        │
└────────────────────────────────────────────┘
```

### Upload Flow

1. User clicks "Upload Service"
2. File picker opens (accepts .json only)
3. User selects service.json file
4. Frontend reads and validates JSON:
   - Check required fields (name, display_name, commands)
   - Validate structure
5. If valid:
   - POST /api/external-services/upload with JSON content
   - Backend saves to `external_services/{name}/service.json`
   - Service appears in Addon Store (type: uploaded)
   - User can now install it like any other service
6. If invalid:
   - Show validation errors
   - User can fix and retry

### API Endpoint

```
POST /api/external-services/upload
Body: {
  "service_definition": {
    "name": "postgres",
    "display_name": "PostgreSQL",
    "config_form": {...},
    "commands": {...},
    ...
  }
}

Response: {
  "success": true,
  "name": "postgres",
  "message": "Service uploaded successfully"
}
```

Backend:
1. Validates JSON structure
2. Checks name doesn't conflict with bundled services
3. Creates `external_services/{name}/` directory
4. Writes to `external_services/{name}/service.json`
5. Service now available in Addon Store

### Validation Rules

**Required fields**:
- `name`
- `display_name`
- `category`
- `commands.install`
- `commands.start`
- `commands.stop`
- `commands.health_check`
- `health_check_expected`

**Optional fields**:
- `description`
- `author`
- `version`
- `config_form`
- `commands.uninstall`
- `commands.restart`
- `commands.enable_startup`
- `commands.disable_startup`
- `required_vars`
- `provides_vars`
- `install_timeout`
- `working_dir`
- `requires_sudo`

### Bundled vs Uploaded Services

**Bundled services**:
- In `external_services/` (git-tracked)
- Shipped with Luna
- Can't be deleted
- Updated with Luna core

**Uploaded services**:
- Also in `external_services/` but git-ignored
- User-added
- Can be deleted
- Must be manually updated

**Conflict prevention**: If user uploads service with same name as bundled service, reject with error.

---

## Benefits

✅ **Single file** - Easy to share and distribute
✅ **Simple upload** - Just drag-and-drop JSON
✅ **Self-contained** - Everything in one place
✅ **Easy to create** - Copy example, modify values
✅ **Version control friendly** - Single file to track
✅ **Template variables** - Simple config substitution
✅ **Flexible** - Can inline simple commands or reference scripts

---

## Example: Simple Redis Service (Complete Single File)

```json
{
  "name": "redis",
  "display_name": "Redis",
  "description": "In-memory data store for caching",
  "category": "cache",
  "author": "Luna Team",
  "version": "7-alpine",
  
  "config_form": {
    "fields": [
      {
        "name": "port",
        "label": "Port",
        "type": "number",
        "default": 6379,
        "required": true
      },
      {
        "name": "password",
        "label": "Password",
        "type": "password",
        "default": "",
        "required": false,
        "help": "Leave empty for no password"
      }
    ]
  },
  
  "commands": {
    "install": "mkdir -p external_services/redis/data .luna/logs && docker run -d --name luna_redis --restart unless-stopped -p {{port}}:6379 {{#if password}}--requirepass {{password}}{{/if}} -v $(pwd)/external_services/redis/data:/data redis:7-alpine >> .luna/logs/redis.log 2>&1",
    "uninstall": "docker stop luna_redis && docker rm luna_redis",
    "start": "docker start luna_redis",
    "stop": "docker stop luna_redis",
    "restart": "docker restart luna_redis",
    "health_check": "docker exec luna_redis redis-cli ping",
    "enable_startup": "docker update --restart=unless-stopped luna_redis",
    "disable_startup": "docker update --restart=no luna_redis"
  },
  
  "health_check_expected": "PONG",
  "install_timeout": 90,
  
  "required_vars": ["REDIS_URL"],
  "provides_vars": ["REDIS_URL", "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"]
}
```

**User can save this as `redis.json` and upload it - that's it!**

---

## Command Execution with Template Variables

When executing commands, backend:

1. Reads saved config from `external_services/{name}/config.json`
2. Replaces `{{variable}}` with values:
   ```
   {{port}} → 5432
   {{database}} → luna
   {{user}} → luna_user
   {{password}} → secure_pass_123
   ```
3. Executes command

For complex logic, can still use `{config_file}` placeholder:
```json
{
  "commands": {
    "install": "bash external_services/postgres/custom_install.sh {config_file}"
  }
}
```

But most services won't need this.

---

## Updated Directory Structure

```
/opt/luna/luna-repo/
├── external_services/       (service definitions + user data)
│   ├── postgres/
│   │   ├── service.json     (definition - keep)
│   │   ├── config.json      (user config - delete on uninstall)
│   │   └── data/            (volumes - delete on uninstall)
│   ├── redis/
│   │   ├── service.json
│   │   ├── config.json
│   │   └── data/
│   └── custom_db/           (user uploaded)
│       ├── service.json
│       ├── config.json
│       └── data/
│
└── .luna/
    └── logs/                (all service logs)
        ├── postgres.log
        ├── redis.log
        └── custom_db.log
```

**In .gitignore**:
```
# User data in external services (keep service.json, ignore config.json and data/)
external_services/*/config.json
external_services/*/data/
```

---

## Answer to Your Question

**Yes - external service is now just a single JSON file!**

You can upload it directly from Infrastructure page. Much simpler than before.