import asyncio
import subprocess
import sys
import time
import os
import json
import re
from fastmcp import Client

# Local imports
from debug.reset_db import reset_database
from db.db_functions import Database, Inventory, TasteProfile, SavedMeals, ShoppingList, DailyPlanner, NewMealIdeas

SERVER_SCRIPT = "mcp_server.py"
SERVER_URL = "http://localhost:8000/sse"

def truncate_output(data, max_length=200):
    """Recursively truncate long strings in a dictionary or list."""
    if isinstance(data, dict):
        return {k: truncate_output(v, max_length) for k, v in data.items()}
    elif isinstance(data, list):
        # If the list is long, truncate it
        if len(data) > 10:
            return [truncate_output(item, max_length) for item in data[:5]] + [f"... ({len(data) - 10} more items) ..."] + [truncate_output(item, max_length) for item in data[-5:]]
        return [truncate_output(item, max_length) for item in data]
    elif isinstance(data, str) and len(data) > max_length:
        return data[:max_length] + "..."
    else:
        return data

class SimpleAgent:
    """Very basic agent that maps keyword phrases to MCP tools."""

    def __init__(self, client: Client):
        self.client = client
        self.tool_map = {
            "inventory context": "pull_get_inventory_context",
            "taste profile": "pull_get_taste_profile_context",
            "saved meals": "pull_get_saved_meals_context",
            "shopping list": "pull_get_shopping_list_context",
            "daily plan": "pull_get_daily_notes_context",
            "meal ideas": "pull_get_new_meal_ideas_context",
            "meals i can make": "pull_get_instock_meals_context",
            "ingredient info": "pull_get_ingredients_info_context",
            "add to inventory": "push_update_inventory",
            "change taste": "push_update_taste_profile",
            "save meal": "push_update_saved_meals",
            "shopping add": "push_update_shopping_list",
            "plan update": "push_update_daily_plan",
            "plan meals": "action_run_meal_planner",
            "suggest meal": "action_run_meal_suggestion_generator",
            "new recipe": "action_run_new_meal_ideator",
        }

    async def run(self, prompt: str) -> str:
        lower = prompt.lower()
        tool = None
        for key, value in self.tool_map.items():
            if key in lower:
                tool = value
                break
        if not tool:
            return "(no tool matched)"

        args = {}
        if tool in {"push_update_inventory", "push_update_saved_meals", "push_update_shopping_list", "push_update_daily_plan"}:
            args["user_input"] = prompt
        elif tool in {"push_update_taste_profile", "action_run_meal_planner", "action_run_meal_suggestion_generator", "action_run_new_meal_ideator"}:
            args["user_request"] = prompt
        
        result = await self.client.call_tool(tool, args)
        if result:
            message = result[0]
            if message and hasattr(message, "text"):
                return message.text
        return ""

# Helper functions to read tables -------------------------------------------

def get_inventory_rows():
    db = Database()
    db.connect(verbose=False)
    rows = Inventory(db).read()
    db.disconnect(verbose=False)
    return rows

def get_taste_profile():
    db = Database()
    db.connect(verbose=False)
    profile = TasteProfile(db).read()
    db.disconnect(verbose=False)
    return profile

def get_saved_meals():
    db = Database()
    db.connect(verbose=False)
    rows = SavedMeals(db).read()
    db.disconnect(verbose=False)
    return rows

def get_shopping_list():
    db = Database()
    db.connect(verbose=False)
    rows = ShoppingList(db).read()
    db.disconnect(verbose=False)
    return rows

def get_daily_plan():
    db = Database()
    db.connect(verbose=False)
    rows = DailyPlanner(db).read()
    db.disconnect(verbose=False)
    return rows

# Test runner ---------------------------------------------------------------

async def run_all_tests():
    results = []
    async with Client(SERVER_URL) as client:
        agent = SimpleAgent(client)

        # Pull tools
        tests = [
            ("inventory context", "please show inventory"),
            ("taste profile", "what is my taste profile"),
            ("saved meals", "list saved meals"),
            ("shopping list", "what is on my shopping list"),
            ("daily plan", "show my daily plan"),
            ("meal ideas", "show new meal ideas"),
            ("meals i can make", "meals i can make"),
            ("ingredient info", "ingredient info"),
        ]
        for key, prompt in tests:
            out = await agent.run(prompt + " " + key)
            results.append({"tool": key, "prompt": prompt, "output": out, "success": bool(out.strip())})

        # Push tools with db checks
        push_tests = [
            ("add to inventory", "add carrots to inventory", get_inventory_rows),
            ("change taste", "i like spicy food", get_taste_profile),
            ("save meal", "save meal grilled cheese", get_saved_meals),
            ("shopping add", "add milk to my shopping list", get_shopping_list),
            ("plan update", "schedule pasta for tomorrow", get_daily_plan),
        ]
        for key, prompt, getter in push_tests:
            before = getter()
            out = await agent.run(prompt + " " + key)
            after = getter()
            success = before != after and bool(out.strip())
            results.append({"tool": key, "prompt": prompt, "output": out, "before": before, "after": after, "success": success})

        # Action tools
        action_tests = [
            ("plan meals", "plan meals for tomorrow"),
            ("suggest meal", "suggest meal for dinner"),
            ("new recipe", "new recipe with chicken"),
        ]
        for key, prompt in action_tests:
            out = await agent.run(prompt + " " + key)
            results.append({"tool": key, "prompt": prompt, "output": out, "success": bool(out.strip())})

    return results

# ---------------------------------------------------------------------------

def llm_evaluate(results):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "LLM evaluation skipped (no API key)"
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        truncated_results = truncate_output(results)

        chat = [
            {"role": "system", "content": "You are a test evaluator."},
            {"role": "user", "content": "Here are JSON test results:"},
            {"role": "user", "content": json.dumps(truncated_results, default=str)}
        ]
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=chat)
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM evaluation failed: {e}"


def main():
    print("Resetting database to sample state...")
    reset_database()

    server = subprocess.Popen([sys.executable, SERVER_SCRIPT])
    try:
        time.sleep(2)
        results = asyncio.run(run_all_tests())
    finally:
        server.terminate()
        server.wait()

    for r in results:
        truncated_r = truncate_output(r)
        print(json.dumps(truncated_r, indent=2, default=str))

    summary = llm_evaluate(results)
    print("\nLLM Evaluation:\n", summary)

if __name__ == "__main__":
    main()
