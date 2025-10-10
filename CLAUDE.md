# Luna Project Schema Definition (v13, MVP-integrated)

Single-source spec with the latest cuts. Minimal, runnable.

---

## 0) Snapshot

* **Services** (each its own process): **Hub UI**, **MCP Server**, **Agent API**.
* **Servers location (for now)**: both **Agent API** and **MCP Server** are single-file modules under `core/utils/`.
* **Auth**: Hub UI + Agent API = localhost only (no auth). MCP = Bearer token.
* **LLM**: default **gpt-4.1** via selector module.
* **Agents**: `simple_agent` (LangChain ReAct), `passthrough_agent` (includes internal **DIRECT_RESPONSE** tool to answer non-tool prompts naturally).
* **Tools**: Python callables, **Pydantic-validated I/O**, opt-in MCP exposure.
* **Memory/Automation**: **Postgres** (UTC in DB; display in **America/New_York**). **Memories = list[str]** (no scopes).
* **Python deps**: **`requirements.txt`**.
* **Secrets**: `.env` in repo root.
* **Agent discovery**: agents discovered at **Hub UI startup** and selectable in UIs (flows/schedules).
* **Auto-update**: field present in extension schema, **not implemented** in MVP.

Default ports: Hub UI `5173`, Agent API `8080`, MCP `8765`, Extension UIs `5200–5299`. Bind `127.0.0.1`.

---

## 1) Project Directory Structure

```
luna/
|-- core/
|   |-- agents/
|   |   |-- simple_agent/
|   |   |-- passthrough_agent/
|   |
|   |-- utils/
|   |   |-- agent_api.py
|   |   |-- mcp_server.py
|   |   |-- llm_selector.py
|   |   |-- prompt_runner.py
|   |   |-- db.py
|   |
|   |-- scripts/
|       |-- start_all.sh
|
|-- extensions/
|   |-- automation_memory/
|   |   |-- readme.md
|   |   |-- config.json
|   |   |-- requirements.txt
|   |   |-- tools/
|   |   |   |-- tool_config.json
|   |   |   |-- automation_memory_tools.py
|   |   |-- ui/
|   |       |-- package.json
|   |       |-- start.sh
|   |       |-- (ui files…)
|   |
|   |-- my_awesome_extension/
|       |-- readme.md
|       |-- config.json
|       |-- requirements.txt
|       |-- tools/
|       |   |-- tool_config.json
|       |   |-- my_awesome_tools.py
|       |-- ui/
|           |-- package.json
|           |-- start.sh
|           |-- (ui files…)
|
|-- hub_ui/
|
|-- .env
|-- requirements.txt
|-- README.md
```

---

## 2) The Hub & Core Systems

### Hub UI

* **Extension management**: load by **local path** or **GitHub URL**. The `auto_update` flag exists but is not implemented.
* **UI aggregation**: for each extension, Hub launches `ui/start.sh <port>`, then iframes it.
* **Navigation**: main menu lists active extension UIs and their health.
* **Env/secret checks**: rendered on **each extension’s page** using its `required_secrets`.
* **Agent discovery**: on startup, Hub discovers agents in `core/agents/` and exposes an **Agent dropdown** in **Task Flows** and **Scheduled Tasks**.
* **Health**: `/healthz`.

### MCP Server (Fast MCP + SSE)

* Exposes tools with `"enabled_in_mcp": true` from all active extensions.
* SSE endpoint (e.g., `/mcp/sse`), Bearer `MCP_AUTH_TOKEN`.
* Single process server module: `core/utils/mcp_server.py`.

### Agent API Server

* **Fully featured OpenAI-compatible server** exposed locally.
* Single file: `core/utils/agent_api.py`.

---

## 3) Extension Schema

### Loading

* **Local Path** or **GitHub URL**. `auto_update` remains in schema but is not implemented.

### Directory

```
<extension>/
|-- readme.md
|-- config.json
|-- requirements.txt
|-- tools/
|   |-- tool_config.json
|   |-- *_tools.py
|-- ui/
    |-- package.json
    |-- start.sh
    |-- (ui files…)
```

### `config.json` (manifest — trimmed)

```json
{
  "name": "my_awesome_extension",
  "required_secrets": ["FOO_API_KEY", "BAR_URL"],
  "auto_update": false
}
```

* Each extension page shows a list of missing `required_secrets` from `.env`.

---

## 4) Tool Schema

### Naming

* `DOMAIN_{GET|UPDATE|ACTION}_VerbNoun`.

### Docstring (required)

1. One-sentence summary.
2. `Example Prompt:` natural language trigger.
3. `Example Response:` compact JSON-like output.
4. `Example Args:` JSON-like args.
5. `Notes:` (optional).

### File format (`*_tools.py`)

```python
from pydantic import BaseModel, Field
from typing import Tuple

SYSTEM_PROMPT = "The user has access to tools for managing their notes."

class NOTES_UPDATE_ProjectNoteArgs(BaseModel):
    project_id: str = Field(...)
    content: str = Field(...)

def NOTES_UPDATE_project_note(project_id: str, content: str) -> Tuple[bool, str]:
    """Append content to today's dated note entry for a project.
    Example Prompt: add "ship MVP" under "Milestones" for project Eco AI
    Example Response: {"project_id": "Eco AI", "success": true}
    Example Args: {"project_id": "string", "content": "string"}
    """
    try:
        _ = NOTES_UPDATE_ProjectNoteArgs(project_id=project_id, content=content)
        return (True, '{"success": true, "project_id": "' + project_id + '"}')
    except Exception as e:
        return (False, f"An error occurred: {e}")

TOOLS = [NOTES_UPDATE_project_note]
```

### `tool_config.json`

```json
{
  "NOTES_UPDATE_project_note": {
    "enabled_in_mcp": true,
    "passthrough": false
  }
}
```

* Inputs validated with **Pydantic** inside the tool.
* Return shape is always `(success: bool, content: str)`.
* Tool names include the extension name; no collision policy required.

---

## 5) UI Schema (Extensions)

* Install: detect `ui/package.json`, run `pnpm install` once.
* Start: run `ui/start.sh <port>`; must serve `/healthz` 200.
* Secret check UX: each extension page shows missing `required_secrets` inline.

---

## 6) Core Agents

### `simple_agent`

* LangChain **ReAct**; may call tools and synthesize results.

### `passthrough_agent`

* Honors `passthrough=true` tools.
* Provides **DIRECT_RESPONSE** internal tool to answer natural prompts with no tool call.

### Error/Retry

* On tool failure `(success=False)`, up to 2 corrective retries; else summarized failure.

### I/O Contract (conceptual)

```python
from pydantic import BaseModel
from typing import List, Optional, Literal

class Msg(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str

class AgentRequest(BaseModel):
    prompt: str
    chat_history: List[Msg] = []
    memory: List[str] = []

class AgentResult(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
```

---

## 7) Built-in Extension: `automation_memory`

**Features**

* **Memories**: append-only list of strings.
* **Scheduled Tasks**: cron-like prompts run via a **selected agent**.
* **Task Flows**: ordered prompts run via a **selected agent**.

**UI**

* Tabs: **Memories**, **Scheduled**, **Flows**.
* Agent dropdowns present in **Scheduled** and **Flows** (agents discovered at Hub startup).

---

## 8) Process Model, Ports, Network

* **Hub UI**: `127.0.0.1:5173`, no auth.
* **Agent API**: `127.0.0.1:8080`, no auth; CORS localhost.
* **MCP**: `127.0.0.1:8765`, Bearer `MCP_AUTH_TOKEN`, SSE at `/mcp/sse`.
* **Extension UIs**: `127.0.0.1:5200–5299`.

---

## 9) Agent API (summary only)

* A **fully featured OpenAI-compatible server** exposed locally, implemented as `core/utils/agent_api.py`.

---

## 10) MCP Server

* SSE endpoint (e.g., `/mcp/sse`) with Bearer `MCP_AUTH_TOKEN`.
* Discovers active extensions and exposes tools where `enabled_in_mcp=true`.

11) Database (Postgres)

* Store timestamps in UTC; display in `America/New_York`.
