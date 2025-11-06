# Quick Start

Get Luna Hub running in 15 minutes. This guide will walk you through the fastest path to your own personal AI hub with extensible tools and agents.

## What is Luna Hub?

Luna Hub is a self-hosted personal AI assistant platform that gives you:

- **AI Agent API**: OpenAI-compatible API for building AI assistants with custom tools
- **MCP Servers**: Connect your AI tools to Claude Desktop and other MCP clients
- **Extension System**: Add capabilities through modular extensions (kitchen management, smart home control, note-taking, etc.)
- **Hub UI**: Web interface for managing everything from one place
- **Privacy First**: Everything runs on your own infrastructure—your data never leaves your control

Think of it as your personal AI infrastructure: instead of relying on cloud services with limited customization, you run Luna Hub on your own hardware and build exactly the assistant you need.

---

## Prerequisites

Before starting, you'll need:

1. **A Linux machine** (Ubuntu, Debian, or compatible)
   - Physical server, cloud VM, or Proxmox container
   - 2GB+ RAM, 10GB+ disk space
   - Root/sudo access

2. **A GitHub account** (for authentication)
   - Sign up at [https://github.com/signup](https://github.com/signup) if you don't have one

3. **An LLM API key** (for AI agents)
   - OpenAI API key ([get one here](https://platform.openai.com/api-keys)), OR
   - Anthropic API key ([get one here](https://console.anthropic.com/))

4. **Network access** (depends on your setup)
   - **Home network?** Get a free [ngrok](https://ngrok.com/signup) account (easiest option)
   - **Cloud VM?** Ensure ports 80 and 443 are open
   - **Custom domain?** Have a domain ready and DNS access

That's it! The installer handles everything else.

---

## Installation (5 Minutes)

### Step 1: Clone and Run Installer

```bash
# Clone the repository
cd /root  # Or your preferred location
git clone https://github.com/jbrinkw/luna-personal-assistant.git
cd luna-personal-assistant

# Run the installer (requires sudo)
sudo ./install.sh
```

The installer will:
- Install all dependencies (Python, Node.js, Docker, Caddy)
- Set up the Python virtual environment
- Configure your deployment mode
- Generate SSL certificates
- Initialize the database
- Start all services

### Step 2: Choose Your Deployment Mode

When prompted, select how you'll access Luna Hub:

```
Choose your deployment mode:
1) ngrok - Tunnel mode (easiest for home networks)
2) nip.io - Auto-detected IP with SSL (cloud VMs)
3) custom_domain - Your own domain (production)
```

**Recommendations:**
- **Home network or testing?** Choose option 1 (ngrok)
- **Cloud VM with public IP?** Choose option 2 (nip.io)
- **Production or custom domain?** Choose option 3 (custom_domain)

See the [Installation Guide](../installation.md#understanding-deployment-modes) for detailed comparisons.

### Step 3: Configure GitHub OAuth

The installer will prompt you to create two GitHub OAuth apps. This takes 2 minutes:

1. Go to [https://github.com/settings/developers](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the details the installer provides (copy/paste)
4. Copy the Client ID and Client Secret back to the installer
5. Repeat for the second app (MCP server)

### Step 4: Add Your API Key

```
Enter your OpenAI API key (or leave empty to configure later):
> sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Paste your OpenAI or Anthropic API key. You can add more keys later through the Hub UI.

### Step 5: Database Setup

```
Install and configure PostgreSQL now? [Y/n]:
> y
```

Press Enter to let the installer set up PostgreSQL automatically.

### Done!

```
=== Installation Complete ===

Luna Hub is accessible at:
https://your-domain

Starting Luna Hub...
```

The installer will start Luna Hub and display your access URL. Open it in your browser!

---

## First Login (2 Minutes)

1. **Navigate to your Luna Hub URL** (from the installer output)

2. **Click "Login with GitHub"**

3. **Authorize the OAuth application**
   - GitHub will ask you to authorize "Luna Hub UI"
   - Click "Authorize"

4. **You're in!** You should see the Luna Hub dashboard with:
   - System status (all services running)
   - Discovered agents (passthrough_agent, simple_agent)
   - Installed extensions (currently none)

---

## Quick Tour (5 Minutes)

### Dashboard

Your landing page shows:
- **System Status**: Are all services running?
- **Discovered Agents**: AI agents available via the Agent API
- **Active Extensions**: What tools are installed?
- **Quick Actions**: Jump to common tasks

### Extensions

Click **Extensions** in the sidebar to browse available extensions:

- **Extension Store**: One-click install of popular extensions (ChefByte, Home Assistant, etc.)
- **Install from GitHub**: Add community extensions via GitHub URL
- **Upload ZIP**: Install custom extension packages

**Try installing an extension:**
1. Click "Extension Store" tab
2. Find an extension (e.g., ChefByte for kitchen management)
3. Click "Install"
4. Restart Luna when prompted

### Tools / MCP Manager

Visit **Tools** to see all available AI tools:

- **Local Tools**: Tools from installed extensions
- **Remote MCP Tools**: Connect to external MCP servers (like Exa search)
- **Toggle Tools**: Enable/disable tools per MCP server or agent preset
- **MCP Connection Details**: Copy connection info for Claude Desktop

### Apps/Services

Click **Apps/Services** to manage external services:

- **Service Marketplace**: One-click install of Docker applications (Grocy, Home Assistant, etc.)
- **Install Service**: Upload custom service definitions
- **Start/Stop/Configure**: Manage installed services

**Try installing a service:**
1. Browse the marketplace
2. Install "Grocy" (household management)
3. Configure settings (ports, passwords)
4. Access the service UI through Luna Hub

### Settings

Visit **Settings → Environment Keys** to manage API keys and secrets:

- View all configured keys (masked for security)
- Add new keys (OpenAI, Anthropic, service-specific)
- Upload `.env` files
- See required keys for installed extensions

---

## Test Your Setup (3 Minutes)

### Test the Agent API

Copy your Agent API key from Settings → Environment Keys, then run:

```bash
curl -X POST https://your-domain/api/agent/v1/chat/completions \
  -H "Authorization: Bearer YOUR_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "passthrough_agent",
    "messages": [{"role": "user", "content": "Hello! What tools do you have access to?"}]
  }'
```

You should get a response from the AI agent listing available tools.

### Test MCP Connection (Optional)

If you use Claude Desktop:

1. Visit **Tools** in Luna Hub
2. Copy the MCP connection JSON
3. Paste it into `claude_desktop_config.json`
4. Restart Claude Desktop
5. Ask Claude: "What MCP tools do you have?"

Claude should list Luna Hub's tools!

---

## What's Next?

Now that Luna Hub is running, here are the best next steps:

### 1. Explore Featured Extensions

See what's possible with Luna Hub by checking out our featured extensions:

- **[ChefByte](featured-extensions.md#chefbyte-your-ai-kitchen-assistant)**: AI kitchen assistant for inventory, meal planning, and nutrition tracking
- **[Home Assistant](featured-extensions.md#home-assistant-voice-controlled-smart-home)**: Voice-controlled smart home integration

These showcase real-world use cases and give you ideas for building your own tools.

### 2. Install an Extension

Visit **Extensions → Extension Store** and install:
- **ChefByte** (if you want to manage your kitchen with AI)
- **Home Assistant** (if you have a smart home setup)
- **Obsidian Sync** (if you use Obsidian for notes)

Each extension adds new tools your AI agents can use.

### 3. Install an App/Service

Visit **Apps/Services** and install:
- **Grocy** (required for ChefByte)
- **PostgreSQL** (if you skipped it during installation)

Services provide the backend infrastructure your extensions connect to.

### 4. Create an Agent Preset

Visit **Tools**, switch to "Agent Presets" mode, and create a specialized agent:

1. Click "Create Agent Preset"
2. Name it (e.g., "smart_home_assistant")
3. Choose a base agent (e.g., "passthrough_agent")
4. Toggle which tools this agent can access
5. Use the agent via the API with `"model": "smart_home_assistant"`

This lets you create focused AI agents for specific tasks (home control, research, coding, etc.).

### 5. Connect External MCP Servers

Visit **Tools**, scroll to "Add Remote MCP Server", and connect:
- **Exa Search** (web search)
- **Context7** (documentation search)
- Any Smithery MCP server

This extends Luna Hub with tools from the broader MCP ecosystem.

### 6. Build Your Own Extension

Ready to create custom tools? Follow the [Developer Guide](../developer-guide/creating-extensions.md) to:
- Create a new extension from scratch
- Add custom AI tools
- Build web UIs for your extensions
- Package and share your extensions

---

## Common Next Questions

### How do I add more API keys?

**Settings → Environment Keys** lets you add any key your extensions need. Just click "Add Key", enter the name and value, and save.

### How do I update Luna Hub?

Use the built-in update system:
1. Visit **Extensions → Update Manager**
2. Check for core updates
3. Queue the update
4. Restart Luna (via the header button)

Or manually:
```bash
cd /root/luna-personal-assistant
git pull origin main
sudo systemctl restart luna
```

### How do I restart Luna?

**Web UI:** Click "Restart" in the header

**Command line:**
```bash
sudo systemctl restart luna
```

### Where are the logs?

```bash
# All logs are in the logs/ directory
tail -f logs/supervisor.log    # Main supervisor
tail -f logs/agent_api.log      # Agent API
tail -f logs/hub_ui.log         # Web UI
tail -f logs/caddy.log          # Reverse proxy

# Or use systemd
journalctl -u luna -f
```

### How do I stop Luna?

```bash
sudo systemctl stop luna
```

### What if something breaks?

Check the [Troubleshooting](../installation.md#troubleshooting) section in the Installation Guide, or:

1. Check service status: `sudo systemctl status luna`
2. View logs: `journalctl -u luna -n 200`
3. Ask in GitHub Issues: [https://github.com/jbrinkw/luna-personal-assistant/issues](https://github.com/jbrinkw/luna-personal-assistant/issues)

---

## Learning More

- **[Installation Guide](../installation.md)**: Detailed installation instructions, deployment modes, and advanced configuration
- **[Featured Extensions](featured-extensions.md)**: Real-world examples of what you can build with Luna Hub
- **[Navigating the Interface](../user-guide/navigating-interface.md)**: Deep dive into the Hub UI
- **[Developer Guide](../developer-guide/creating-extensions.md)**: Build your own extensions and tools

---

## Get Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/jbrinkw/luna-personal-assistant/issues)
- **Documentation**: Browse the full docs at your Luna Hub under `/docs`
- **Developer Chat**: Join discussions in GitHub Issues

Welcome to Luna Hub! 🎉
