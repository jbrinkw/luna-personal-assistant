# Luna - AI Agent Platform

Luna is a modular AI agent platform that provides:
- Multiple agent implementations (ReAct, Passthrough with DIRECT_RESPONSE)
- OpenAI-compatible Agent API
- MCP (Model Context Protocol) server for tool exposure
- Extension system for adding custom tools and UIs
- Built-in automation & memory management

## Architecture

### Core Services

1. **Agent API** (`core/utils/agent_api.py`) - Port 8080
   - OpenAI-compatible chat completions API
   - Discovers agents from `core/agents/*/agent.py`
   - No authentication (localhost only)

2. **MCP Server** (`core/utils/mcp_server.py`) - Port 8765
   - SSE transport with Bearer token auth
   - Exposes tools with `enabled_in_mcp: true`

3. **Hub UI** (`hub_ui/`) - Port 5173
   - Extension management (load from path or GitHub)
   - UI aggregation via iframes
   - Agent discovery and health monitoring

### Agents

- **simple_agent**: LangChain ReAct with all discovered tools
- **passthrough_agent**: Planner-executor with passthrough routing and DIRECT_RESPONSE tool

### Extensions

Extensions live in `extensions/` with structure:
```
extension_name/
├── readme.md
├── config.json
├── requirements.txt
├── tools/
│   ├── tool_config.json
│   └── *_tools.py
└── ui/
    ├── package.json
    ├── start.sh
    └── (React/Vite app)
```

Built-in extensions:

**automation_memory**
- Memories (contextual information)
- Scheduled tasks (cron-like execution)
- Task flows (sequential prompts)

**home_assistant**
- Control Home Assistant devices (lights, switches, fans, media players)
- Natural language entity control via friendly names
- TV remote control with app launching
- Device status queries

## Setup

### 1. Prerequisites

- Python 3.10+
- Node.js 18+ and pnpm
- PostgreSQL 14+

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required variables:
- `DB_*` - Postgres connection details
- `OPENAI_API_KEY` - For gpt models
- `MCP_AUTH_TOKEN` - For MCP server authentication
- `HA_URL` - Home Assistant instance URL (e.g., `http://192.168.1.100:8123`)
- `HA_TOKEN` - Home Assistant long-lived access token
- `HA_REMOTE_ENTITY_ID` - (Optional) TV remote entity ID (defaults to `remote.living_room_tv`)

### 4. Initialize Database

```bash
python core/scripts/init_db.py
```

### 5. Install Extension UIs

```bash
# For automation_memory
cd extensions/automation_memory/ui
pnpm install
cd ../../..
```

### 6. Start Services

#### Option A: Individual Services

```bash
# Agent API
python core/utils/agent_api.py

# MCP Server
python core/utils/mcp_server.py

# Hub UI
cd hub_ui
pnpm install
pnpm dev
```

#### Option B: All-in-One Script

```bash
# Linux/Mac/WSL
./core/scripts/start_all.sh

# Windows
core\scripts\start_all.bat
```

## Usage

### Agent API

OpenAI-compatible endpoint at `http://127.0.0.1:8080`:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8080/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="simple_agent",  # or "passthrough_agent"
    messages=[
        {"role": "user", "content": "What tools do you have access to?"}
    ]
)

print(response.choices[0].message.content)
```

### MCP Server

Connect using SSE transport with Bearer token:

```
http://127.0.0.1:8765/sse
Authorization: Bearer <MCP_AUTH_TOKEN>
```

### Hub UI

Access at `http://127.0.0.1:5173` to:
- Manage extensions
- View agent health
- Access extension UIs in iframes

## Development

### Creating an Extension

1. Create directory structure in `extensions/your_extension/`
2. Define `config.json` with name and required secrets
3. Create tools in `tools/*_tools.py`:
   - Follow naming: `DOMAIN_{GET|UPDATE|ACTION}_VerbNoun`
   - Use Pydantic for validation
   - Return `(bool, str)` tuples
   - Include Example Prompt/Response/Args in docstrings

4. Configure `tools/tool_config.json`:
```json
{
  "YOUR_TOOL_name": {
    "enabled_in_mcp": true,
    "passthrough": false
  }
}
```

5. Create UI (optional) in `ui/` with React+Vite

### Creating an Agent

1. Create directory in `core/agents/your_agent/`
2. Implement `agent.py` with:
   - `async def run_agent(user_prompt, chat_history, memory, tool_root, llm) -> AgentResult`
   - `async def run_agent_stream(...)` for streaming
   - `initialize_runtime()` for setup

3. Agent will be auto-discovered by Agent API

## Port Allocation

- **5173**: Hub UI
- **8080**: Agent API
- **8765**: MCP Server
- **3051**: Automation Memory backend (Node.js)
- **5200-5299**: Extension UIs

All services bind to `127.0.0.1` (localhost only)

## Database Schema

Tables created by `init_db.py`:

- **task_flows**: Task flow definitions with agent selection
- **scheduled_prompts**: Scheduled task configurations
- **memories**: Context storage

All timestamps in UTC (TIMESTAMPTZ), displayed in America/New_York.

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python tests/test_simple_agent.py
```

## Troubleshooting

### Database Connection Errors
- Verify Postgres is running
- Check DB_* environment variables in `.env`
- Run `python core/scripts/init_db.py` to initialize schema

### Agent Not Found
- Ensure agent has `async def run_agent()` function
- Check Agent API logs for discovery issues
- Verify agent.py is in `core/agents/*/agent.py`

### Extension Tools Not Loading
- Check tool file naming: `*_tools.py`
- Verify `TOOLS = [...]` list is exported
- Check `tool_config.json` syntax

### MCP Auth Failures
- Verify `MCP_AUTH_TOKEN` in `.env`
- Use Bearer token in Authorization header
- Check MCP server logs

## License

[Your License]

## Contributing

[Contributing guidelines]

