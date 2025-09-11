# Basic hierarchical agent

The basic hierarchical agent decomposes a user request into domain-specific intents, executes each intent within the appropriate extension using a focused sub-agent, then synthesizes a single final response.

This pattern mirrors the system described in `personal_assistant_readme.md`: a one-shot Router, multiple domain sub-agents (react style), and a one-shot Synthesizer.

## Architecture

1. Router (one-shot)
   - Reads the Light Schema (derived from loaded extensions)
   - Segments the user prompt into per-extension intents
   - Does not pick specific tools

2. Domain sub-agents (react, multi-step)
   - One sub-agent per targeted extension
   - Use the extension’s full system prompt and tool docstrings
   - Plan → call tools → observe → repeat until done

3. Synthesizer (one-shot)
   - Merges all domain returns with user context
   - Resolves conflicts
   - Produces the final message

For the Light Schema details, see: Core → Agent helpers → Light schema.

## Data flow (minimal example)

- Input: "add milk to my inventory and return my workout plan for today"
- Router → `ChefByte (add milk to inventory)`, `CoachByte (return workout plan)`
- ChefByte sub-agent → uses `CHEFBYTE_UPDATE_ITEM` → confirmation
- CoachByte sub-agent → uses `COACHBYTE_GET_WORKOUT_TODAY` → plan
- Synthesizer → one combined reply

## Agent I/O contract (minimal)

All agents in Luna should support a minimal interface for interoperability. See Core → Agent Format for the canonical spec. At a glance, the agent returns:

- content: final response text
- response_time_secs: total wall-clock seconds
- traces: tool calls (name, output, args, durations)

Sub-agents may return additional fields internally, but the outer contract should include at least these fields.

## When to use this agent

- You want strong separation between routing, domain reasoning, and synthesis
- You have multiple domains (extensions) and need clear tool orchestration
- You prefer concise, deterministic routing context (Light Schema)

## Notes

- Keep extension system prompts crisp (first line = domain summary)
- Structure tool docstrings consistently to power reliable routing
- Favor small, composable tools for better planning and reuse
