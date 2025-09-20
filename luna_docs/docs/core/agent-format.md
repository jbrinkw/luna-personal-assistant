# Agent Format — Minimum Interface Spec

This document defines the minimal, implementation-agnostic interface that all agents must support. Agents may add richer inputs/outputs, but these fields and behaviors are mandatory for easy integration across the system.

See also: `personal_assistant_readme.md` for architecture (Router, Domain Agents, Synthesizer, Light Schema).

---

### Function signature (required)

- async run_agent(prompt: str, chat_history: Optional[str] = None, memory: Optional[str] = None, config: Optional[dict] = None)

Notes:
- **prompt**: required latest user message.
- **chat_history**: optional string. Suggested format (line-based):
  - `user: ...`
  - `assistant: ...`
- **memory**: optional string of extra context.
- **config**: optional dict to override per-call behavior (see below). Agents can safely ignore unknown keys.
- Agents may accept additional kwargs (e.g., `tool_root`), but must support the above.

---

### Return shape (required fields)

- **content**: string — final response text.
- **response_time_secs**: number — total wall-clock seconds for the call.
- **traces**: array — zero or more tool calls (empty if no tools are used).

Tool trace item (each):
- **tool**: string — tool name.
- **output**: string — tool result serialized to text.
- **args**: object (optional) — JSON-serializable arguments.
- **duration_secs**: number (optional) — wall-clock seconds for the tool call.

Minimal JSON example:

```json
{
  "content": "Here is your plan for today...",
  "response_time_secs": 2.81,
  "traces": [
    {
      "tool": "COACHBYTE_GET_WORKOUT_TODAY",
      "args": {"date": "2025-09-10"},
      "output": "{\"plan\":\"...\"}",
      "duration_secs": 0.34
    }
  ]
}
```

Language-agnostic JSON schema (draft):

```json
{
  "type": "object",
  "required": ["content", "response_time_secs", "traces"],
  "properties": {
    "content": { "type": "string" },
    "response_time_secs": { "type": "number" },
    "traces": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["tool", "output"],
        "properties": {
          "tool": { "type": "string" },
          "output": { "type": "string" },
          "args": { "type": "object" },
          "duration_secs": { "type": "number" }
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": true
}
```

Python reference types (optional, for Python agents):

```python
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ToolTraceMinimal(BaseModel):
    tool: str
    output: str
    args: Optional[Dict[str, Any]] = None
    duration_secs: Optional[float] = None

class AgentOutputMinimal(BaseModel):
    content: str
    response_time_secs: float
    traces: List[ToolTraceMinimal] = Field(default_factory=list)
```

---

### Config (optional per-call overrides)

Recognized keys (stable):
- **tool_root**: string — directory to discover extensions under.
- **only_domains**: list[string] — restrict execution to these domain/extension names.
- **execution_mode**: 'async' | 'threads' — broadcast-style agents only.
- **domain_timeout_secs**: number — per-domain timeout (overrides env).
- **model_overrides**: { 'router'|'domain'|'synth': string } — force specific model IDs per role.

Rules:
- If both env vars and `config` are present, **config wins** for that call.
- Agents may add more keys; unknown keys are ignored.

---

### Compatibility and extensions

- Agents may return additional fields (e.g., `results`, `timings`, `models`).
- Test runners and servers will prefer the minimal fields when present.
- Tool names should be deduplicated when surfaced to callers; order should reflect first occurrence.

---

### Selecting the active agent

- Set `ACTIVE_AGENT_PATH` in your environment to point to any agent module path (relative to repo root). Example:

```bash
ACTIVE_AGENT_PATH=core/agent/hierarchical.py
```

The CLI/server load the active agent from this path and will still work with agents that return additional fields beyond the minimum spec.


