# Tool Overview

This document explains each tool available in the project and how they connect to form the overall "ChefByte" assistant.

## UPDATE Tools

Push tools modify database records based on natural language. They are served via
`push_tools.py` using FastMCP.  Each function returns a confirmation string.

| Tool (function) | Arguments | Returns | Example |
|-----------------|-----------|---------|---------|
| `CHEF_UPDATE_inventory` | `user_input: str` | `str` summary of changes | `"add 2 apples"` |
| `CHEF_UPDATE_taste_profile` | `user_request: str` | `str` confirmation | `"i prefer spicy food"` |
| `CHEF_UPDATE_saved_meals` | `user_input: str` | `str` confirmation | `"save meal lasagna"` |
| `CHEF_UPDATE_shopping_list` | `user_input: str` | `str` confirmation | `"add milk to my list"` |
| `CHEF_UPDATE_daily_plan` | `user_input: str` | `str` confirmation | `"schedule pasta tomorrow"` |

These tools connect to the [pull helpers](../helpers/push_helpers/) which parse the text and apply updates using the database layer.

## GET Tools

Pull tools fetch context from the database via `pull_tools.py`.  Each function
returns formatted text describing the requested information.

| Tool (function) | Arguments | Returns | Example |
|-----------------|-----------|---------|---------|
| `CHEF_GET_inventory_context` | none | `str` inventory summary | `"show inventory"` |
| `CHEF_GET_taste_profile_context` | none | `str` description | `"what do i like"` |
| `CHEF_GET_saved_meals_context` | none | `str` listing | `"list saved meals"` |
| `CHEF_GET_shopping_list_context` | none | `str` list | `"what do i need"` |
| `CHEF_GET_daily_notes_context` | none | `str` upcoming plan | `"show daily plan"` |
| `CHEF_GET_new_meal_ideas_context` | none | `str` new ideas | `"show new ideas"` |
| `CHEF_GET_instock_meals_context` | none | `str` meals using inventory | `"what can i cook now"` |
| `CHEF_GET_ingredients_info_context` | none | `str` ingredient info | `"ingredient info"` |

## ACTION Tools

Action tools orchestrate higher‑level workflows. They are defined in
`action_tools.py` and typically call multiple helper layers.

| Tool (function) | Arguments | Returns | Example |
|-----------------|-----------|---------|---------|
| `CHEF_ACTION_run_meal_planner` | `user_request: str` | `str` final plan | `"plan meals for next week"` |
| `CHEF_ACTION_run_meal_suggestion_generator` | `user_request: str` | `str` suggestions | `"suggest meal for dinner"` |
| `CHEF_ACTION_run_new_meal_ideator` | `user_request: str` | `str` recipe or idea | `"new recipe with chicken"` |

### Meal Planner Layers

1. **Intent generation** – extract date range and create meal intents for each day.
2. **Meal selection** – pick specific meal IDs for breakfast, lunch and dinner using the intents.

### New Meal Ideator Layers

1. **Descriptions** – produce numbered meal ideas based on taste profile and inventory.
2. **Recipes** – upon request, build detailed recipes for selected ideas.
3. **Save** – optionally translate ingredients to IDs and store the new meals in the database.

## MCP Server

`mcp_server.py` aggregates the servers into a single FastMCP endpoint. Each tool can be called via SSE/HTTP or stdio. Example start command:

```bash
python mcp_server.py --host 0.0.0.0 --port 8000
```

Clients then call tool names such as `CHEF_GET_inventory_context` or `CHEF_UPDATE_inventory` over the selected transport.
The exposed function names match those listed above (for example `CHEF_UPDATE_inventory` or `CHEF_GET_inventory_context`).

## Database Layer

All tools rely on the database utilities in `db/db_functions.py`. The `init_tables` and `with_db` helpers create tables and manage connections. Tables include `inventory`, `taste_profile`, `saved_meals`, `shopping_list`, and others.

