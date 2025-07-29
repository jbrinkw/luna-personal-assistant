import asyncio
import subprocess
import sys
import time
import sqlite3
import os
import json
import re
from fastmcp import Client

# Local imports
from debug.reset_db import reset_database
from db.db_functions import Database, Inventory, TasteProfile, SavedMeals, ShoppingList, DailyPlanner, NewMealIdeas

SERVER_SCRIPT = "mcp_server.py"
SERVER_URL = "http://localhost:8000/mcp"

class SimpleAgent:
    """Very basic agent that maps keyword phrases to MCP tools."""

    def __init__(self, client: Client):
        self.client = client
        self.tool_map = {
            "inventory context": "get_inventory_context",
            "taste profile": "get_taste_profile_context",
            "saved meals": "get_saved_meals_context",
            "shopping list": "get_shopping_list_context",
            "daily plan": "get_daily_notes_context",
            "meal ideas": "get_new_meal_ideas_context",
            "meals i can make": "get_instock_meals_context",
            "ingredient info": "get_ingredients_info_context",
            "add to inventory": "update_inventory",
            "change taste": "update_taste_profile",
            "save meal": "update_saved_meals",
            "shopping add": "update_shopping_list",
            "plan update": "update_daily_plan",
            "plan meals": "run_meal_planner",
            "suggest meal": "run_meal_suggestion_generator",
            "new recipe": "run_new_meal_ideator",
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
        if tool in {"update_inventory", "update_saved_meals", "update_shopping_list", "update_daily_plan"}:
            args["user_input"] = prompt
        elif tool in {"update_taste_profile", "run_meal_planner", "run_meal_suggestion_generator", "run_new_meal_ideator"}:
            args["user_request"] = prompt
        
        result = await self.client.call_tool(tool, args)
        return result.content[0].text if result.content else ""

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
        chat = [
            {"role": "system", "content": "You are a test evaluator."},
            {"role": "user", "content": "Here are JSON test results:"},
            {"role": "user", "content": json.dumps(results)}
        ]
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=chat)
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
        print(json.dumps(r, indent=2, default=str))

    summary = llm_evaluate(results)
    print("\nLLM Evaluation:\n", summary)

if __name__ == "__main__":
    main()
