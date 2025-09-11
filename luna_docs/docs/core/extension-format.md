# Extension Format — Authoring

## What is an extension?
- Extension: a self-contained domain pack that provides:
  - NAME: human-readable domain name
  - SYSTEM_PROMPT: domain instructions (first line is the domain summary)
  - TOOLS: a list of callable Python functions (tools)
- Extensions are discovered automatically anywhere under `extensions/` by scanning for files named `*_tool.py`.

## File and naming conventions
- Forward-facing tool file name: `<domain>_tool.py` (must end with `_tool.py`). Examples:
  - `extensions/notes/notes_tool.py`
  - `extensions/home_assistant/home_assistant_tool.py`
- Module-level symbols (required) in the forward-facing tool file:
  - `NAME: str` — display name (e.g., "Notes")
  - `SYSTEM_PROMPT: str` — domain prompt; the first non-empty line is used as the domain summary in the Light Schema
  - `TOOLS: list[Callable]` — Python callables to expose as tools

## Tool function naming
- Prefer: `DOMAIN_{GET|UPDATE|ACTION}_VerbNoun`
  - Examples: `NOTES_GET_project_hierarchy`, `COACHBYTE_UPDATE_summary`, `GENERAL_ACTION_send_phone_notification`
- Keep names descriptive and stable; tool names are surfaced to the agent directly.

## Tool docstring structure (required)
Each tool function’s docstring should follow this structure:
- Line 1: Summary (one sentence)
- Line 2: `Example Prompt: ...` (natural-language trigger)
- Line 3: `Example Response: {...}` (compact, JSON-like)
- Line 4: `Example Args: {...}` (argument names, types, brief hints)
- Line 5..n: Additional notes (optional)

Why: The system derives a Light Schema for routing using the summary and the first non-empty line after it. Using `Example Prompt:` ensures consistent parsing. Domain agents see the full docstring.

Example:
```python
def NOTES_UPDATE_project_note(project_id: str, content: str, section_id: Optional[str] = None) -> UpdateProjectNoteResponse | OperationResult:
    """Append content to today's dated note entry for a project. Creates file/entry if needed.
    Example Prompt: add "ship MVP" under "Milestones" for project Eco AI
    Example Response: {"project_id": "Eco AI", "note_file": ".../Notes.md", "created_entry": true, "appended": true}
    Example Args: {"project_id": "string[id or display name]", "content": "string[text]", "section_id": "string[optional]"}
    Notes: Validates project existence; creates today's entry if missing.
    """
```

## Argument typing and outputs
- Add precise type hints for all parameters; default to `str`, `int`, `float`, `bool`, `Optional[...]` as appropriate
- For structured outputs, prefer returning Pydantic models; the agent normalizes results to strings for context
- Keep tool return payloads concise; avoid large blobs unless necessary

## Environment configuration
- Load `.env` when available (dotenv supported)
- Read environment via `os.getenv(...)`
- Document required env vars in the module docstring or tool notes (e.g., `HA_URL`, `HA_TOKEN`, `TAVILY_API_KEY`)

## Discovery and Light Schema
- Discovery scans for any `*_tool.py` file under `extensions/`
- A valid extension module exports `NAME`, `SYSTEM_PROMPT`, and `TOOLS`
- Light Schema per extension includes:
  - `NAME — <first line of SYSTEM_PROMPT>`
  - For each tool: `- <tool_name>: <summary> EX: "<first non-empty line after summary>"`

## Checklist to add a new extension
1. Create `extensions/<your_extension>/<your_extension>_tool.py`
2. Define `NAME`, `SYSTEM_PROMPT` (first line = summary), and `TOOLS`
3. Implement tools with the required docstring structure and type hints
4. Prefer Pydantic models for structured outputs
5. Note any required environment variables
6. Run the agent; the extension will be discovered automatically

## Examples in repo
- `extensions/notes/notes_tool.py`
- `extensions/home_assistant/home_assistant_tool.py`
- `extensions/generalbyte/generalbyte_tool.py`
- `extensions/todo_list/todo_list_tool.py`


