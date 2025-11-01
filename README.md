# Luna Hub

**Your private AI platform for managing AI tools and self-hosted applications**

[![Documentation](https://img.shields.io/badge/docs-live-blue)](https://jbrinkw.github.io/luna-personal-assistant/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/jbrinkw/luna-personal-assistant?style=social)](https://github.com/jbrinkw/luna-personal-assistant)

---

> **A Note from Jeremy, the Developer:**
>
> Luna Hub is a platform for hosting and managing all of your AI tools and self-hosted applications. I originally started this project as a way to host a custom tool set for my [Home Assistant Voice Preview](https://www.home-assistant.io/voice_pe/), which is basically just a self-hosted Alexa. As time went on I realized this could be useful to a lot of people, so I built it out into a platform that would be easy for anyone to use.
>
> Please let me know if you have any questions or feature requests at [jeremy@onthebrink.ai](mailto:jeremy@onthebrink.ai). I hope you enjoy it as much as I do!

---

## What is Luna Hub?

Luna Hub is your **private, self-hosted platform** for managing AI tools and local applications. It puts you in complete control of your AI assistant infrastructure—running entirely on your hardware, whether that's a home server, cloud VM, or always-on computer.

Think of it as **mission control for your personal AI ecosystem**—install tools, deploy apps, and connect them to AI agents through natural language.

### Key Features

- 🎯 **OpenAI-Compatible Agent API** - Build custom AI applications using any OpenAI SDK
- 🔌 **MCP (Model Context Protocol)** - Connect your tools to Claude Desktop and other MCP clients
- 🧩 **Extensible Architecture** - Install AI tools from the built-in store or create your own
- 🐳 **Docker App Management** - One-click deployment of self-hosted applications
- 🔐 **GitHub OAuth** - Secure authentication with optional username restrictions
- 🌐 **Unified Web Interface** - Manage extensions, apps, tools, and configuration from a single dashboard
- 🔒 **Complete Privacy** - All processing happens on your hardware

## Quick Start

### Prerequisites

- Linux operating system (Debian, Ubuntu, or compatible)
- 2+ GB RAM (4+ GB recommended)
- 20+ GB free disk space
- Root/sudo access

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jbrinkw/luna-personal-assistant.git
   cd luna-personal-assistant
   ```

2. **Run the installer:**
   ```bash
   sudo ./install.sh
   ```

3. **Choose your deployment mode:**
   - **Ngrok**: Easiest for home networks (requires ngrok account)
   - **Nip.io**: Dynamic DNS for cloud VMs (requires open ports 80/443)
   - **Custom domain**: Production setup with your own domain

4. **Set up GitHub OAuth:**
   - Create a GitHub OAuth App at https://github.com/settings/developers
   - Enter credentials during installation

5. **Access Luna Hub:**
   - Open your browser to your configured domain
   - Log in with GitHub
   - Start installing extensions and apps!

📖 **Full installation guide**: [Installation Documentation](https://jbrinkw.github.io/luna-personal-assistant/installation/)

## What Can You Build?

### 🍳 Kitchen & Nutrition Assistant

Install **ChefByte** and **Grocy** to create an AI-powered kitchen manager:

- *"What's in my pantry?"* → Get real-time inventory with expiration dates
- *"Add milk to my shopping list"* → Voice-controlled shopping lists
- *"What can I cook tonight?"* → Recipe suggestions based on current inventory
- *"Log my breakfast: 2 eggs and toast"* → Track nutrition and calories

### 🏠 Smart Home Voice Control

Install **Home Assistant extension** to control your entire home:

- *"Turn on the living room lights"* → Direct device control
- *"Is the garage door open?"* → Real-time status queries
- *"Set movie mode"* → Trigger multi-device scenes
- Build your own private Alexa alternative

### 🤖 Custom AI Agents

Create specialized agents with filtered tool access:

- **Smart home assistant**: Only home automation tools
- **Meal planning assistant**: Only kitchen and recipe tools
- **Research assistant**: Only web search and documentation

## Architecture

Luna Hub is built on a modular architecture:

### Components

- **Extensions**: AI tools (Python functions) that agents can call
- **Apps/Services**: Self-hosted Docker applications (Grocy, PostgreSQL, etc.)
- **Agent API**: OpenAI-compatible API server for custom applications
- **MCP Servers**: Industry-standard protocol for Claude Desktop integration
- **Hub UI**: React-based web interface for management

### Technology Stack

- **Backend**: Python (FastAPI), LangChain, FastMCP
- **Frontend**: React, Vite, TailwindCSS
- **Proxy**: Caddy (automatic HTTPS)
- **Containers**: Docker, Docker Compose
- **Auth**: GitHub OAuth
- **Database**: PostgreSQL (optional, for session persistence)

## Documentation

📚 **Full documentation available at**: https://jbrinkw.github.io/luna-personal-assistant/

- [Installation Guide](https://jbrinkw.github.io/luna-personal-assistant/installation/) - Complete setup instructions
- [Featured Extensions](https://jbrinkw.github.io/luna-personal-assistant/getting-started/featured-extensions/) - ChefByte and Home Assistant walkthroughs
- [Creating Extensions](https://jbrinkw.github.io/luna-personal-assistant/developer-guide/creating-extensions/) - Build your own tools
- [Architecture](https://jbrinkw.github.io/luna-personal-assistant/reference/architecture/) - Technical deep dive

## Featured Extensions

### ChefByte (Kitchen Management)

Connects to Grocy for AI-powered household management:
- Inventory tracking with expiration dates
- Smart shopping lists
- Meal planning and recipe management
- Nutrition tracking and macros
- Price tracking for groceries

### Home Assistant

Control your smart home through natural language:
- Device control (lights, switches, thermostats)
- Status queries for all devices
- Media control (TVs, speakers)
- Complex automation and scenes

### Automation Memory

Built-in memory and task scheduling:
- Persistent conversation memory
- Scheduled task execution
- Workflow automation
- Cross-session context retention

## Example Use Cases

### Morning Routine
```
"Good morning, what's on my schedule?"
```
→ Agent checks calendar, weather, and suggests breakfast based on pantry inventory

### Cooking Assistant
```
"I want to make dinner with chicken and rice"
```
→ Agent searches recipes, checks ingredients, adds missing items to shopping list

### Smart Home Automation
```
"I'm going to bed"
```
→ Agent locks doors, turns off lights, sets thermostat, and arms security

### Grocery Management
```
"What groceries do I need this week?"
```
→ Agent analyzes meal plan, checks inventory, generates shopping list with costs

## Privacy & Control

Unlike commercial AI assistants, Luna Hub offers:

- ✅ **Complete data sovereignty** - All processing on your hardware
- ✅ **No cloud dependencies** - Core functionality works offline (LLM API calls excepted)
- ✅ **Open source** - Audit, modify, and contribute
- ✅ **Self-hostable** - Run anywhere Docker runs
- ✅ **Conversation privacy** - Queries stay on your network
- ✅ **Data control** - You decide what's stored and for how long

## Contributing

Contributions are welcome! Please feel free to:

- Report bugs or request features via [GitHub Issues](https://github.com/jbrinkw/luna-personal-assistant/issues)
- Submit pull requests for improvements
- Share your custom extensions with the community
- Improve documentation

## Support

- 📧 Email: [jeremy@onthebrink.ai](mailto:jeremy@onthebrink.ai)
- 🐛 Issues: [GitHub Issues](https://github.com/jbrinkw/luna-personal-assistant/issues)
- 📖 Docs: [Full Documentation](https://jbrinkw.github.io/luna-personal-assistant/)

## License

[MIT License](LICENSE) - See LICENSE file for details

---

**Luna Hub is mission control for your personal AI ecosystem—bringing together tools, apps, and AI agents on your infrastructure, under your control.**
