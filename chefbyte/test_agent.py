import asyncio
import subprocess
import sys
import time
import json

from agents import Agent
from agents.mcp.server import MCPServerSse, MCPServerSseParams
from agents.run import Runner

from debug.reset_db import reset_database
from db.db_functions import Database, Inventory, TasteProfile, SavedMeals, ShoppingList, DailyPlanner

SERVER_PORT = 8000
SERVER_URL = f"http://localhost:{SERVER_PORT}/sse"
SERVER_SCRIPT = "chefbyte/chefbyte_mcp_server.py"
MODEL = "gpt-4o"

# ---------------------------------------------------------------------
# Helper functions for DB snapshots

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

# ---------------------------------------------------------------------
async def run_agent(prompt: str) -> str:
    server = MCPServerSse(MCPServerSseParams(url=SERVER_URL))
    await server.connect()
    agent = Agent(
        name="ChefByteTest",
        instructions="You are testing the ChefByte tools. Use them to satisfy the user request.",
        mcp_servers=[server],
        model=MODEL,
    )
    result = await Runner.run(agent, prompt)
    await server.cleanup()
    return result.final_output

async def test_table(before_fn, prompt_update, prompt_view):
    before = before_fn()
    update_out = await run_agent(prompt_update)
    after = before_fn()
    view_out = await run_agent(prompt_view)
    return {
        "before": before,
        "update_output": update_out,
        "after": after,
        "query_output": view_out,
    }

async def run_tests():
    results = {}
    results["inventory"] = await test_table(get_inventory_rows, "add carrots to inventory", "show inventory")
    results["taste_profile"] = await test_table(get_taste_profile, "i like spicy food", "what is my taste profile")
    results["saved_meals"] = await test_table(get_saved_meals, "save meal grilled cheese", "list saved meals")
    results["shopping_list"] = await test_table(get_shopping_list, "add milk to my shopping list", "show shopping list")
    results["daily_planner"] = await test_table(get_daily_plan, "schedule pasta for tomorrow", "show my daily plan")
    return results

# ---------------------------------------------------------------------
def llm_judge(results: dict) -> str:
    try:
        import openai
        client = openai.OpenAI()
        chat = [
            {"role": "system", "content": "You evaluate whether each table update succeeded based on before/after data."},
            {"role": "user", "content": json.dumps(results, default=str)},
        ]
        resp = client.chat.completions.create(model=MODEL, messages=chat)
        return resp.choices[0].message.content
    except Exception as e:
        return f"LLM judge failed: {e}"

# ---------------------------------------------------------------------
def main():
    print("Resetting ChefByte database...")
    reset_database()
    server = subprocess.Popen([sys.executable, SERVER_SCRIPT, "--port", str(SERVER_PORT)])
    try:
        time.sleep(2)
        results = asyncio.run(run_tests())
    finally:
        server.terminate()
        server.wait()
    print(json.dumps(results, indent=2, default=str))
    judgment = llm_judge(results)
    print("\nLLM Evaluation:\n", judgment)

if __name__ == "__main__":
    main()
