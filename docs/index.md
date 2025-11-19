!!! note "Hello from Jeremy, the Developer!"
    This is just the AI preview of the docs. I'll go back and replace the AI slop with real human words when I get a chance, but I have read everything and it is accurate if not just a bit verbose.

    In my own words, Luna Hub is a platform for hosting and managing all of your AI tools and self-hosted applications. I originally started this project as a way to host a custom tool set for my [Home Assistant Voice Preview](https://www.home-assistant.io/voice_pe/), which is basically just a self-hosted Alexa, and to host my custom toolset to an AI chat. Originally I was going to use an API/locally driven AI model for my custom toolset, but then Anthropic and ChatGPT added support for remote MCP servers and that's a lot more accessible and cheaper because I'm already paying for my usage there anyways. As time went on I realized this could be useful to a lot of people, so I built it out into a platform that would be easy for anyone to use. I really enjoyed working on this and learned a lot of technical skills and got a lot of experience with product design. Please let me know if you have any questions or feature requests at [jeremy@onthebrink.ai](mailto:jeremy@onthebrink.ai). I hope you enjoy it as much as I do!

# What Luna Hub Can Do For You

Luna Hub is your **private, self-hosted platform for managing AI tools and local applications**. It puts you in complete control of your AI assistant infrastructure—running entirely on your hardware, whether that's a home server, cloud VM, or always-on computer.

Unlike cloud-based AI assistants that send your data to third parties and lock you into pre-built integrations, Luna Hub is a **unified platform** that:

- **Manages AI tools** through an extensible architecture
- **Orchestrates self-hosted applications** via Docker
- **Provides multiple AI surfaces** (OpenAI API, MCP servers, web UIs)
- **Keeps everything private** on your infrastructure

Think of it as **mission control for your personal AI ecosystem**—install tools, deploy apps, and connect them to AI agents through natural language.

## What Makes Luna Hub Different

### 🎯 A Platform, Not Just an Assistant

Luna Hub isn't a single AI assistant—it's a **platform for building AI experiences**:

- **Build voice assistants** that control your home and access your data
- **Connect to Claude Desktop** via MCP and give it access to your tools
- **Create specialized agents** with filtered tool access for specific tasks
- **Access tools directly** through extension web UIs when you don't need AI

### 🔌 Two Types of Components: Extensions & Apps/Services

**Extensions** provide **AI tools** (Python functions) that agents can call:
- ChefByte: Kitchen inventory, meal planning, nutrition tracking
- Home Assistant: Smart home device control
- Automation Memory: Task scheduling and memory management
- **Browse the built-in store** for easy one-click installation
- Install from GitHub or upload custom packages

**Apps/Services** are **self-hosted applications** Luna manages for you:
- Grocy: Household management web app with inventory, recipes, meal planning
- PostgreSQL: Database for storing agent memory and automation data
- **Built-in marketplace** with pre-configured Docker applications
- Upload custom service definitions or install from the store
- One-click deployment, health monitoring, automatic restarts

### 🤖 Multiple Ways to Access Your Tools

Luna Hub exposes your tools through several interfaces:

**1. OpenAI-Compatible Agent API** (port 8080)
- Build custom AI applications using any OpenAI SDK
- **Example**: Voice assistant on your phone that controls lights, checks pantry inventory, and plans meals
- Compatible with any OpenAI client
- Streaming support for real-time responses

**2. MCP Servers** (Model Context Protocol)
- Connect your tools to Claude Desktop and other MCP clients
- Multiple servers for different use cases (`main`, `smarthome`, `research`)
- GitHub OAuth authentication or API key access
- Industry-standard protocol from Anthropic

**3. Extension Web UIs**
- Direct browser access to extension interfaces
- No AI needed when you want manual control
- Embedded in Luna's unified interface

**4. Apps/Services Web UIs**
- Full-featured web applications (like Grocy)
- Automatically proxied and secured through Luna
- Works standalone or AI-enhanced through extensions

## Core Capabilities

### 🔧 Extensible Tool System

Luna's power comes from its **extension architecture**. Each extension can provide:

- **Custom tools**: Python functions that AI agents can call
- **Web interfaces**: Optional UIs embedded in the Hub
- **Background services**: Long-running processes with health monitoring
- **Configuration management**: Per-extension settings and secrets

**Featured extension: ChefByte** (kitchen & nutrition management)

ChefByte connects to Grocy (a self-hosted household management app) and provides AI-powered tools for:

- **Inventory management**: "What do I have in my pantry?" → Get real-time inventory with quantities and expiration dates
- **Smart shopping lists**: "Add milk to my shopping list" → Automatically tracks items you need
- **Meal planning**: "What can I cook tonight?" → Get recipe suggestions based on your current inventory
- **Nutrition tracking**: "Log my breakfast: 2 eggs and toast" → Track macros and calories throughout the day
- **Recipe management**: Store and organize your favorite recipes with ingredient lists
- **Price tracking**: Monitor grocery prices over time

All through **natural conversation** with your AI agent—no app switching, no manual data entry. Your agent can autonomously check inventory, suggest meals, and help you plan a week of dinners based on what you already have.

**Featured extension: Home Assistant**

Control your entire smart home through natural language:

- **Device control**: "Turn on the living room lights" → Direct control of lights, switches, thermostats
- **Status queries**: "Is the garage door open?" → Real-time device state information
- **Media control**: "Play music in the bedroom" → Control TVs, speakers, and media players
- **Complex automation**: "Set movie mode" → Trigger multi-device scenes

**Example use case**: Build a voice assistant app on your phone that connects to Luna's Agent API. Ask it to turn off the lights, check your pantry, and add items to your shopping list—all with **your custom tools**, not limited to what commercial assistants allow. Your conversations stay on your network, and you control exactly what data is stored and for how long.

### 🐳 Apps/Services Management

Luna deploys and manages **Docker-based applications** that run alongside your extensions:

- **One-click installation**: Deploy complex applications from the Hub UI
- **Integrated proxying**: Apps automatically exposed through Luna's reverse proxy with authentication
- **Health monitoring**: Automatic restarts when apps become unhealthy
- **Configuration management**: Web-based configuration forms for each app
- **Persistent data**: Docker volumes for databases and app data

**Featured app: Grocy**

Grocy is a powerful household management web application that Luna can deploy and manage:

- **Web-based interface**: Full-featured UI accessible at `/apps_services/grocy/`
- **Persistent data**: All your inventory and meal plans stored locally in Docker volumes
- **API access**: ChefByte extension connects to Grocy's API to provide AI-powered interactions
- **Standalone operation**: Use Grocy directly through its web UI or enhance it with AI tools

This demonstrates Luna's **hybrid approach**: run sophisticated web apps for direct access, then layer AI capabilities on top for natural language control. Grocy works perfectly on its own, but with ChefByte installed, you can interact with it through conversation.

### 🌐 MCP (Model Context Protocol) Integration

Luna Hub implements **Anthropic's MCP standard**, making your tools available to Claude Desktop and any other MCP-compatible clients:

- **GitHub OAuth authentication**: Secure access to your personal assistant from Claude
- **Multiple MCP servers**: Create specialized servers for different use cases
  - `main`: GitHub OAuth, full tool access
  - `smarthome`: API key auth, only home automation tools
  - `research`: API key auth, only web search and docs tools
- **API key management**: Generate and rotate keys through the Hub UI
- **Remote MCP servers**: Connect to Smithery's ecosystem (web search, documentation, etc.)

**Example**: Chat with Claude Desktop and have it access your home automation, kitchen inventory, calendar, and any other tools you've installed—all through the standardized MCP protocol.

### 📊 Intelligent Agent Presets

Create **specialized AI agents** with custom tool access for the Agent API:

- **Smart home assistant**: Access only home automation tools (no kitchen/shopping access)
- **Meal planning assistant**: Access only ChefByte and recipe tools
- **Research assistant**: Access only web search and documentation tools

Each preset uses a base agent architecture (like `passthrough_agent`) but filters the available tools, ensuring agents have just the capabilities they need—nothing more, nothing less.

Build different mobile apps or voice interfaces that each connect to a different agent preset, giving you specialized assistants for specific tasks.

### 🔐 GitHub OAuth & Secure Access

Luna Hub includes enterprise-grade authentication:

- **GitHub OAuth integration**: Secure login using your GitHub account
- **Username restrictions**: Optionally limit access to specific GitHub users
- **Session management**: Secure cookie-based sessions with optional database persistence
- **Caddy reverse proxy**: All services (extensions, apps, APIs) protected behind a single authentication layer

### 🛠️ Unified Management Interface

The **Hub UI** (built with React + Vite) provides a centralized dashboard for:

- **Extension marketplace**: Install extensions from GitHub or upload custom packages
- **Tool manager**: Enable/disable individual tools per MCP server or agent preset
- **Apps/Services**: Install, configure, and manage self-hosted applications
- **Service monitoring**: Real-time status of all running processes
- **Environment configuration**: Manage API keys and secrets through a web interface
- **Update queue**: Stage multiple changes and apply them with a single restart

## Privacy & Control

Unlike commercial AI assistants, Luna Hub offers:

- **Complete data sovereignty**: All processing happens on your hardware
- **No cloud dependencies**: Core functionality works entirely offline (LLM API calls excepted)
- **Open source**: Audit the code, modify behavior, contribute improvements
- **Self-hostable**: Run on Raspberry Pi, home server, cloud VM, or anywhere Docker runs
- **Conversation privacy**: Your queries never leave your network unless you explicitly connect external LLM APIs
- **Data control**: You decide what's stored, for how long, and who has access

## Real-World Use Cases

### Morning Routine Assistant
*"Good morning, what's on my schedule?"*
→ Agent checks calendar, weather, commute time, and suggests breakfast based on pantry inventory

### Cooking Assistant
*"I want to make dinner with chicken and rice"*
→ Agent searches recipes, checks if you have ingredients, adds missing items to shopping list, and walks you through cooking steps

### Smart Home Automation
*"I'm going to bed"*
→ Agent locks doors, turns off lights, sets thermostat, arms security system, and sets a morning alarm

### Grocery Management
*"What groceries do I need this week?"*
→ Agent analyzes meal plan, checks current inventory, generates shopping list with estimated costs

### Health & Fitness Tracking
*"Log today's meals and show my macros"*
→ Agent records food intake, calculates nutrition, compares to goals, and suggests adjustments

### Research & Documentation
Connect Luna to Claude Desktop via MCP, then ask Claude to search the web, check your local documentation, and pull information from your knowledge base—all while chatting naturally.

## Getting Started

Ready to build your private AI platform? Check out the [Installation Guide](installation.md) to get Luna Hub running on your infrastructure in under 15 minutes.

Want to explore what's possible? See [Featured Extensions](getting-started/featured-extensions.md) for detailed examples of ChefByte and Home Assistant integrations.

---

**Luna Hub is mission control for your personal AI ecosystem—bringing together tools, apps, and AI agents on your infrastructure, under your control.**
