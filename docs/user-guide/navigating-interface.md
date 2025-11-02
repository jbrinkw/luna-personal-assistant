# Navigating the Interface

Luna's web interface is designed to be simple and intuitive. This guide will help you find your way around.

---

## Overview & Layout

After logging in with your GitHub account, you'll land on the **Dashboard**. The interface has three main areas:

- **Header**: Contains navigation links, system controls (Restart button), and the Update Manager badge
- **Main Content**: The primary workspace that changes based on which page you're viewing
- **Navigation**: Menu or tabs to move between different sections

---

## Dashboard

The Dashboard is your home base. It shows:

- **Quick Stats**: Number of extensions, tools, agents, and external services you have installed
- **Quick Actions**: Tiles linking to key pages (Extensions, Tools, External Services)
- **System Status**: Health indicators showing if everything is running properly

---

## Extension Manager

Extensions add new capabilities to Luna. The Extension Manager lets you:

### Installing Extensions

**From GitHub:**

1. Click "Install from GitHub"
2. Enter the repository URL (e.g., `github:username/repo`)
3. For monorepos, add the subdirectory path (e.g., `github:user/repo:extensions/myext`)
4. Click Install

**From ZIP File:**

1. Click "Upload Extension"
2. Select your `.zip` file
3. Click Install

### Managing Extensions

- **Enable/Disable**: Toggle extensions on or off without uninstalling
- **View Details**: See extension info, version, and required configuration
- **Uninstall**: Remove extensions you no longer need

**Note:** Most changes require a system restart to take effect.

---

## Tool & MCP Manager

This is where you control which tools are available to your AI agents and MCP clients.

### Mode Toggle

At the top right, toggle between:

- **MCP Mode**: Manage MCP servers and their tool access
- **Agent Presets Mode**: Create custom agents with filtered tool sets

### MCP Mode

**MCP Server Pills**: Click to select which server you're configuring (main, smarthome, research, etc.)

**Managing Servers:**

- **main**: Your primary server (uses GitHub OAuth, cannot be deleted)
- **Custom Servers**: Create additional servers with their own API keys
- View/copy API keys with the eye icon
- Regenerate keys when needed

**Adding Remote MCP Servers:**

1. Scroll to "Add Remote MCP Server"
2. Enter the Smithery MCP server URL (includes API key)
3. Click Add
4. Toggle individual tools on/off for that server

**Tool Toggles:**

- **Remote MCP Tools**: Tools from Smithery servers (Exa search, Context7, etc.)
- **Local Extension Tools**: Tools from your installed extensions
- Toggle them on/off for the selected server

**Quick Actions**: Enable or disable all tools at once

### Agent Presets Mode

Create specialized agents that only have access to specific tools.

**Creating a Preset:**

1. Enter a preset name (e.g., "smart_home_assistant")
2. Select a base agent (usually "passthrough_agent")
3. Click Create

**Managing Presets:**

- Select a preset from the pills
- Toggle which tools it can access
- Rename or delete presets
- View the shared API key (same for all presets)

**Use Case Example:** Create a "research_agent" that only has web search tools, or a "home_agent" that only controls smart home devices.

---

## External Services

External Services are dockerized applications (databases, apps, etc.) that Luna can manage.

### Installing Services

1. Browse available services (Postgres, Grocy, etc.)
2. Click "Install"
3. Fill out the configuration form (ports, passwords, etc.)
4. Click Save

### Managing Services

- **Start/Stop/Restart**: Control service lifecycle
- **Enable/Disable**: Auto-start on Luna boot
- **View UI**: Click the service link to open its web interface
- **View Logs**: Check service output for troubleshooting
- **Uninstall**: Remove the service and its data

**Status Indicators:**

- Green: Running and healthy
- Yellow: Starting or unhealthy
- Red: Stopped or failed

---

## Environment & Configuration

### Environment Key Manager

Safely store API keys, passwords, and other secrets.

- **View Keys**: See your configured environment variables (values are masked)
- **Add/Update**: Create new keys or update existing ones
- **Delete**: Remove keys you no longer need
- **Upload .env**: Bulk import keys from a file

**Required Secrets**: Extensions will show which environment variables they need.

---

## Update Queue & Changes

Luna uses a queue system for updates to prevent breaking changes.

### How It Works

1. Make changes (install extensions, toggle tools, etc.)
2. Changes are queued, not applied immediately
3. The Update Manager badge shows pending changes
4. Click **Restart Luna** to apply all queued changes

### Reviewing the Queue

1. Click the Update Manager badge
2. Review operations: installs, updates, deletes
3. Clear the queue if you change your mind
4. Restart to apply

**Why?** This ensures all related changes happen together and the system stays consistent.

---

## System Controls

### Restart Luna

Applies all pending changes and restarts services. The interface will be unavailable for 30-60 seconds.

### Shutdown

Gracefully stops all Luna services. You'll need to restart manually via command line or systemd.

---

## Common Workflows

### First-Time Setup

1. **Dashboard**: Check that core services are running
2. **Environment Keys**: Add required API keys (OpenAI, GitHub, etc.)
3. **Extensions**: Install extensions for features you want
4. **Restart**: Apply changes
5. **Tools**: Enable tools for your MCP servers/agents

### Adding a Smart Home Extension

1. Install Home Assistant extension
2. Add `HA_URL` and `HA_TOKEN` in Environment Keys
3. Restart Luna
4. Go to Tool Manager → Create "home_agent" preset
5. Enable only Home Assistant tools for that preset
6. Use the preset's API key in your AI client

### Setting Up Postgres

1. Go to External Services
2. Install Postgres
3. Configure database name, user, password
4. Start the service
5. Note the connection details for your extensions

---

## Navigation Tips

- **Status Indicators**: Green = good, Yellow = warning, Red = problem
- **Restart Required**: Most config changes need a restart to take effect
- **API Keys**: Shown with eye icons - click to reveal, click again to hide
- **Logs**: If something isn't working, check the logs first
- **Quick Actions**: Look for "Enable All" / "Disable All" buttons to save time

---

## Getting Help

- Check the logs for error messages
- Review the extension's README for configuration requirements
- Ensure all required environment variables are set
- Try restarting Luna after configuration changes
- Check GitHub issues or documentation for known problems
