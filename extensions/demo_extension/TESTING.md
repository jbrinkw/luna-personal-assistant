# Testing Demo Extension Services

This document explains how to manually test the demo extension services.

## Directory Structure

```
demo_extension/
├── config.json
├── readme.md
├── TESTING.md (this file)
└── services/
    ├── web_server/
    │   ├── service_config.json
    │   ├── start.sh
    │   └── server.py
    └── background_worker/
        ├── service_config.json
        ├── start.sh
        └── worker.py
```

## Service 1: Web Server (requires port)

### Configuration
- **Requires port**: Yes
- **Health check**: `/healthz`
- **Restart on failure**: Yes

### Manual Testing

Start the web server on port 5350:
```bash
cd extensions/demo_extension/services/web_server
./start.sh 5350
```

Test the health check endpoint:
```bash
curl http://127.0.0.1:5350/healthz
# Expected response: {"status": "healthy", "service": "web_server"}
```

Test the demo endpoint:
```bash
curl http://127.0.0.1:5350/demo
# Returns JSON with demo information
```

Test the info endpoint:
```bash
curl http://127.0.0.1:5350/info
# Returns service information
```

## Service 2: Background Worker (no port)

### Configuration
- **Requires port**: No
- **Health check**: None
- **Restart on failure**: Yes

### Manual Testing

Start the background worker:
```bash
cd extensions/demo_extension/services/background_worker
./start.sh
```

You should see log output like:
```
[2025-10-18 12:34:56] Background Worker started
[2025-10-18 12:34:56] This service runs without requiring a network port
[2025-10-18 12:35:06] Background Worker tick #1 - Processing tasks...
```

Press Ctrl+C to stop the worker gracefully.

## How Supervisor Will Handle These Services

### Web Server
1. Supervisor reads `service_config.json` and sees `requires_port: true`
2. Assigns port from range 5300-5399 (e.g., 5300)
3. Saves assignment to `master_config.json` under `port_assignments.services["demo_extension.web_server"]`
4. Starts service: `./start.sh 5300`
5. Polls health check every 30 seconds: `GET http://127.0.0.1:5300/healthz`
6. If health check fails twice, restarts the service (up to 2 restart attempts)

### Background Worker
1. Supervisor reads `service_config.json` and sees `requires_port: false`
2. No port assignment needed
3. Starts service: `./start.sh` (no port argument)
4. No health check polling (health_check is null)
5. Process monitoring only - restarts if process exits unexpectedly

## Expected Port Assignments

When this extension is loaded, the master_config.json will include:

```json
{
  "port_assignments": {
    "services": {
      "demo_extension.web_server": 5300,
      "demo_extension.background_worker": null
    }
  }
}
```

## LUNA_PORTS Environment Variable

Both services will receive this environment variable:

```json
{
  "core": {
    "hub_ui": 5173,
    "agent_api": 8080,
    "mcp_server": 8765
  },
  "extensions": {},
  "services": {
    "demo_extension.web_server": 5300,
    "demo_extension.background_worker": null
  }
}
```

Services can parse this to discover other service ports for inter-service communication.

## Integration with Luna

To enable this extension:

1. Add to `master_config.json`:
```json
{
  "extensions": {
    "demo_extension": {
      "enabled": true,
      "source": "local",
      "config": {}
    }
  }
}
```

2. Restart Luna system
3. Supervisor will discover and start both services automatically
4. View service status in Hub UI Services tab

