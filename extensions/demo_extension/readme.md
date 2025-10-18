# Demo Extension

This is a demonstration extension showcasing two different types of services:

1. **Web Server** - A service that requires a port and provides a health check endpoint
2. **Background Worker** - A service that runs without requiring a network port

## Services

### Web Server (`web_server`)
- Requires port: Yes
- Health check: `/healthz`
- Description: Simple HTTP server that responds to health checks and provides a demo endpoint

### Background Worker (`background_worker`)
- Requires port: No
- Health check: None
- Description: Background task that logs messages every 10 seconds

## Usage

These services are started automatically by the Luna supervisor when the extension is enabled.

Access the web server at: `http://127.0.0.1:{assigned_port}/`

