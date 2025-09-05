# Personal Assistant — Router + Domain Agents

## Overview
Modular, tool-calling agent. **Router** and **Synthesizer** are **one-shot**.  
**Domain modules** are **react agents** that can take multiple steps (plan → act → observe → repeat) before returning a result.

Extensions provide the domain’s system prompt and tool list. The router uses a **Light Schema** (derived on the fly) to segment user requests across extensions. Domain sub-agents use the **full** system prompt + docstrings and call tools directly.

---

## Light Schema
**Purpose:** a minimal, natural-language view the router uses to segment a user request across extensions.  
**Source:** directly from loaded **extensions** (derived at runtime; may be cached).  
**Format:** **Natural language**, not JSON.

**Per extension, include:**
- **Domain summary** — the **first non-empty line** of the extension’s system prompt.
- **Tools list** — each tool line shows:
  - **Tool name** (e.g., `CHEFBYTE_UPDATE_ITEM`)
  - **Summary** — docstring **line 1**
  - **Example** — docstring **line 2**

**Tiny example**
```
ChefByte — Manage kitchen inventory and meal planning for the user.
- CHEFBYTE_UPDATE_ITEM: Updates a single item quantity and unit. EX: "Set milk to 1 gallon."
- CHEFBYTE_GET_INVENTORY: Returns current inventory snapshot. EX: "How many gallons of milk do I have left?"

CoachByte — Plan and track workouts for the user.
- COACHBYTE_GET_WORKOUT_TODAY: Returns today’s workout plan. EX: "What’s my workout plan for today?"
```

---

## Extension Authoring Format

### Tool naming (required)
```
DOMAIN_{GET|UPDATE|ACTION}_TOOLNAME
```
Examples: `CHEFBYTE_GET_INVENTORY`, `COACHBYTE_UPDATE_SET_LOG`, `CHEFBYTE_ACTION_CREATE_MEALPLAN`

### System Prompt (per extension)
- **Line 1:** **Domain summary** (one sentence).
- **Line 2..n:** deeper explanation + notes (used by the domain agent).

**Example**
```
Manage kitchen inventory and meal planning for the user.
Use precise units; prefer pantry items; ask before destructive changes.
```

### Tool Docstring (per tool)
- **Line 1:** simple sentence explaining the tool (**summary**).
- **Line 2:** an **example prompt** that should trigger/use this tool.
- **Line 3..n:** notes (optional).

**Example (`CHEFBYTE_UPDATE_ITEM`)**
```
Updates a single item quantity and unit.
Set milk to 1 gallon.
Idempotent; validates unit compatibility.
```

---

## Agent Stack — Data Flow

1. **Inputs**
   - **Extensions**: { system prompt, tool docstrings }
   - `user_prompt`, `chat_history`, `memory/context`

2. **Router (segmentation only, one-shot)**
   - Reads the **Light Schema** view derived from extensions.
   - Segments the user prompt into **per-extension intents** (no tool selection).
   - Example  
     User: `add milk to my inventory and return my workout plan for today`  
     Router → `ChefByte (add milk to inventory)`, `CoachByte (return workout plan)`

3. **Domain Sub-Agents (react, multi-step)**
   - One sub-agent per targeted extension.
   - Receives the **extracted intent** from the router.
   - Uses **full system prompt + full tool docstrings**; plans and calls tools over multiple steps.
   - Returns **data/confirmation** when done.

4. **Response Synthesizer (one-shot)**
   - Merges all domain returns with `user_prompt + chat_history + memory`.
   - Resolves conflicts; emits the final reply.

---

## Data Visibility

| Component        | Sees                                                                                          |
|------------------|-----------------------------------------------------------------------------------------------|
| Router           | **Light Schema (natural language)**, `user_prompt`, `chat_history`, `memory`                  |
| Domain sub-agent | Full **system prompt**, full **tool docstrings**, tools, `user_prompt`, `chat_history`, `memory` |
| Synthesizer      | Domain returns (data/confirmations) + `user_prompt`, `chat_history`, `memory`                 |

---

## Minimal Behavior Example

- Input: `add milk to my inventory and return my workout plan for today`
- Router → `ChefByte (add milk to inventory)`, `CoachByte (return workout plan)`
- ChefByte sub-agent → uses `CHEFBYTE_UPDATE_ITEM` (react loop if needed) → confirmation  
- CoachByte sub-agent → uses `COACHBYTE_GET_WORKOUT_TODAY` (react if needed) → plan  
- Synthesizer → one combined message

---

## Notes
- The Light Schema is intentionally tiny to keep router context small and deterministic.
- Concurrency, timeouts, and retries are handled inside domain sub-agents; router and synthesizer stay single-shot.
