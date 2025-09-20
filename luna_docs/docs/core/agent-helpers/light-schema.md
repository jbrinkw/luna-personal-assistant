# Light Schema — Concept and Interface

### What it is
**Light Schema** is a compact, natural‑language snapshot of each extension’s domain and surface area. The Router reads it to segment a user request across extensions. It is intentionally tiny, human‑readable text — not JSON.

### Why it exists
- **Keep routing deterministic**: small, focused context helps the Router cleanly segment intents.
- **Lower token footprint**: only what the Router needs (no verbose tool docs).
- **Fast setup**: derived on the fly from loaded extensions; can be cached for reuse.

### What it contains (per extension)
- **Domain summary**: the first non‑empty line of the extension’s `SYSTEM_PROMPT`.
- **Tools list**: one line per tool in the form `TOOL_NAME: <summary> EX: "<example>"` where:
  - summary = docstring line 1
  - example = first non‑empty line after the summary

### How the system uses it
- **Router**: reads Light Schema and returns per‑extension intents (no tool selection).
- **Domain sub‑agents**: do not use Light Schema; they see the full system prompt and full tool docstrings.
- **Synthesizer**: unaffected; it merges domain outputs.

### Where it comes from
- Built at runtime from the code under `extensions/`.
- Implemented in `core/helpers/light_schema_gen.py` (`discover_extensions`, `build_light_schema_for_extension`, `build_all_light_schema`).
- Preloaded/cached by `core/agent/hierarchical.py` via `initialize_runtime(...)` and `_get_light_schema(...)`.

### How to interface with it
- **Inspect in a terminal**
```bash
python -m core.helpers.light_schema_gen | cat
```

- **Use in code**
```python
from core.helpers.light_schema_gen import build_all_light_schema

schema_text = build_all_light_schema()
print(schema_text)
```

- **Runtime preload (recommended for the agent runloop)**
```python
from core.agent.hierarchical import initialize_runtime

initialize_runtime(tool_root=None)  # or a custom path containing *_tool.py files
```

### Authoring guidelines (so Light Schema is high‑quality)
- **System prompt**: make line 1 a crisp one‑sentence summary of the domain.
- **Tool docstrings**: ensure line 1 is a clear summary; line 2 is a concrete example trigger.
- **Naming**: prefer `DOMAIN_{GET|UPDATE|ACTION}_TOOLNAME` (e.g., `CHEFBYTE_GET_INVENTORY`).
- **Keep examples short**: they should be recognizable triggers the Router can reason about.

### Tiny example
```
ChefByte — Manage kitchen inventory and meal planning for the user.
- CHEFBYTE_UPDATE_ITEM: Updates a single item quantity and unit. EX: "Set milk to 1 gallon."
- CHEFBYTE_GET_INVENTORY: Returns current inventory snapshot. EX: "How many gallons of milk do I have left?"

CoachByte — Plan and track workouts for the user.
- COACHBYTE_GET_WORKOUT_TODAY: Returns today’s workout plan. EX: "What’s my workout plan for today?"
```

### Non‑goals
- Not a full API spec or parameter schema.
- Not used for tool selection or planning — only routing.
- Not intended to contain long explanations or multi‑line notes.

### Troubleshooting
- **Empty output**: ensure there are files matching `*_tool.py` under `extensions/` and each defines `NAME`, `SYSTEM_PROMPT`, and `TOOLS` (callables).
- **Stale content after changes**: re‑run `initialize_runtime(...)` so cached schema refreshes.

