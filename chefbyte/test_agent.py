"""
Comprehensive ChefByte MCP Server Test Suite

This test suite evaluates all ChefByte tools using OpenAI Agents SDK with GPT-4.1.
It tests CRUD operations on all database tables and uses LLM judging to evaluate
functionality. The database is reset to sample data before each test run.

Test Categories:
1. CRUD Tests - Test database operations for each table
2. Action Tools - Test high-level meal planning and suggestion tools  
3. Pull Tools - Test data retrieval functions
4. Push Tools - Test data modification functions
"""

import asyncio
import subprocess
import sys
import time
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from agents import Agent
from agents.mcp.server import MCPServerSse, MCPServerSseParams
from agents.run import Runner

# Load environment variables
load_dotenv()

from debug.reset_db import reset_database
from db.db_functions import Database, Inventory, TasteProfile, SavedMeals, ShoppingList, DailyPlanner, NewMealIdeas

SERVER_PORT = 8000
SERVER_URL = f"http://localhost:{SERVER_PORT}/sse"
SERVER_SCRIPT = "chefbyte/chefbyte_mcp_server.py"
MODEL = "gpt-4o"

# ---------------------------------------------------------------------
# Database Snapshot Functions

def get_inventory_snapshot():
    """Get current inventory state"""
    db = Database()
    db.connect(verbose=False)
    rows = Inventory(db).read()
    db.disconnect(verbose=False)
    return [dict(row) if hasattr(row, '_asdict') else row for row in rows] if rows else []

def get_taste_profile_snapshot():
    """Get current taste profile state"""
    db = Database()
    db.connect(verbose=False)
    profile = TasteProfile(db).read()
    db.disconnect(verbose=False)
    return profile

def get_saved_meals_snapshot():
    """Get current saved meals state"""
    db = Database()
    db.connect(verbose=False)
    rows = SavedMeals(db).read()
    db.disconnect(verbose=False)
    return [dict(row) if hasattr(row, '_asdict') else row for row in rows] if rows else []

def get_shopping_list_snapshot():
    """Get current shopping list state"""
    db = Database()
    db.connect(verbose=False)
    rows = ShoppingList(db).read()
    db.disconnect(verbose=False)
    return [dict(row) if hasattr(row, '_asdict') else row for row in rows] if rows else []

def get_daily_planner_snapshot():
    """Get current daily planner state"""
    db = Database()
    db.connect(verbose=False)
    rows = DailyPlanner(db).read()
    db.disconnect(verbose=False)
    return [dict(row) if hasattr(row, '_asdict') else row for row in rows] if rows else []

def get_new_meal_ideas_snapshot():
    """Get current new meal ideas state"""
    db = Database()
    db.connect(verbose=False)
    rows = NewMealIdeas(db).read()
    db.disconnect(verbose=False)
    return [dict(row) if hasattr(row, '_asdict') else row for row in rows] if rows else []

# ---------------------------------------------------------------------
# Agent Interaction Functions

async def run_agent(prompt: str, timeout: int = 15) -> str:
    """Run agent with given prompt and return response"""
    server = None
    try:
        server = MCPServerSse(MCPServerSseParams(url=SERVER_URL))
        await asyncio.wait_for(server.connect(), timeout=5)
        
        agent = Agent(
            name="ChefByteTestAgent",
            instructions="""You are a comprehensive testing agent for ChefByte tools. 
            Use the available tools to satisfy user requests. Be thorough and specific in your responses.
            When viewing data, provide detailed information about what you find.""",
            mcp_servers=[server],
            model=MODEL,
        )
        
        result = await asyncio.wait_for(Runner.run(agent, prompt), timeout=timeout)
        return result.final_output
        
    except asyncio.TimeoutError:
        return f"Agent error: Request timed out after {timeout} seconds"
    except Exception as e:
        return f"Agent error: {str(e)}"
    finally:
        if server:
            try:
                await asyncio.wait_for(server.cleanup(), timeout=2)
            except:
                pass

# ---------------------------------------------------------------------
# CRUD Testing Functions

async def test_crud_operation(table_name: str, snapshot_fn, update_prompt: str, query_prompt: str) -> Dict[str, Any]:
    """Test CRUD operation on a table with before/after snapshots"""
    print(f"  Testing {table_name} CRUD operations...")
    
    # Get before state
    before_state = snapshot_fn()
    
    # Execute update operation
    update_result = await run_agent(update_prompt)
    
    # Get after state  
    after_state = snapshot_fn()
    
    # Execute query operation
    query_result = await run_agent(query_prompt)
    
    return {
        "table": table_name,
        "before_state": before_state,
        "update_prompt": update_prompt,
        "update_result": update_result,
        "after_state": after_state,
        "query_prompt": query_prompt,
        "query_result": query_result,
        "state_changed": before_state != after_state
    }

async def run_crud_tests() -> Dict[str, Any]:
    """Run comprehensive CRUD tests on all tables"""
    print("Running CRUD tests...")
    
    crud_tests = {
        "inventory": await test_crud_operation(
            "inventory",
            get_inventory_snapshot,
            "Add 2 pounds of ground turkey to the inventory with expiration date next week",
            "Show me the complete current inventory including quantities and expiration dates"
        ),
        
        "taste_profile": await test_crud_operation(
            "taste_profile", 
            get_taste_profile_snapshot,
            "Update my taste profile to include that I love Mediterranean food and am trying to eat more vegetables",
            "What does my current taste profile say about my food preferences?"
        ),
        
        "saved_meals": await test_crud_operation(
            "saved_meals",
            get_saved_meals_snapshot, 
            "Save a new meal called 'Turkey Meatball Pasta' with ground turkey, pasta, marinara sauce, and parmesan cheese. It takes 25 minutes to prepare.",
            "List all my saved meals with their ingredients and prep times"
        ),
        
        "shopping_list": await test_crud_operation(
            "shopping_list",
            get_shopping_list_snapshot,
            "Add Greek yogurt, spinach, and olive oil to my shopping list",
            "Show me everything currently on my shopping list"
        ),
        
        "daily_planner": await test_crud_operation(
            "daily_planner", 
            get_daily_planner_snapshot,
            "Schedule 'Chicken Caesar Salad' for lunch tomorrow and 'Spaghetti Carbonara' for dinner the day after tomorrow",
            "Show me my meal plan for the next 3 days"
        )
    }
    
    return crud_tests

# ---------------------------------------------------------------------
# Tool-Specific Testing Functions

async def test_action_tools() -> Dict[str, Any]:
    """Test high-level action tools"""
    print("Testing action tools...")
    
    action_tests = {
        "meal_planner": await run_agent(
            "Help me plan meals for the next 3 days using ingredients I have in my inventory. Consider my taste preferences."
        ),
        
        "meal_suggestions": await run_agent(
            "Generate 5 meal suggestions that I can make with chicken, pasta, and vegetables. Make them family-friendly."
        ),
        
        "meal_ideation": await run_agent(
            "Come up with 3 creative new meal ideas using ground beef and cheese as main ingredients. Include cooking instructions."
        )
    }
    
    return action_tests

async def test_pull_tools() -> Dict[str, Any]:
    """Test data retrieval tools"""
    print("Testing pull tools...")
    
    pull_tests = {
        "get_inventory": await run_agent("What ingredients do I currently have in my kitchen inventory?"),
        "get_taste_profile": await run_agent("What are my taste preferences and dietary restrictions?"),
        "get_saved_meals": await run_agent("What meals have I saved that I can cook?"),
        "get_shopping_list": await run_agent("What items are on my shopping list?"),
        "get_daily_plan": await run_agent("What meals do I have planned for the coming days?"),
        "get_in_stock_meals": await run_agent("What saved meals can I make with my current inventory?"),
        "get_meal_ideas": await run_agent("What new meal ideas do you have for me?")
    }
    
    return pull_tests

async def test_push_tools() -> Dict[str, Any]:
    """Test data modification tools beyond basic CRUD"""
    print("Testing push tools...")
    
    push_tests = {
        "complex_inventory_update": await run_agent(
            "I used 1 pound of ground beef, 2 cups of pasta, and half a jar of marinara sauce for dinner tonight. Update my inventory."
        ),
        
        "taste_profile_refinement": await run_agent(
            "I've discovered I don't like cilantro and I'm trying to reduce sodium in my diet. Update my preferences."
        ),
        
        "meal_modifications": await run_agent(
            "I want to modify my 'Chicken Caesar Wrap' recipe to be healthier - use grilled chicken instead of fried and add more vegetables."
        ),
        
        "shopping_list_management": await run_agent(
            "I bought milk and eggs from my shopping list. Remove them and add items needed for making pancakes this weekend."
        ),
        
        "daily_notes_update": await run_agent(
            "Add a note that I really enjoyed the pasta dish I made yesterday and want to make it again next week with more garlic."
        )
    }
    
    return push_tests

# ---------------------------------------------------------------------
# LLM Judging Functions

def create_llm_judge_prompt(test_results: Dict[str, Any]) -> str:
    """Create comprehensive prompt for LLM judge"""
    return f"""
You are an expert software testing judge evaluating the functionality of ChefByte MCP tools.

Analyze the following test results and provide a comprehensive assessment:

TEST RESULTS:
{json.dumps(test_results, indent=2, default=str)}

For each test category, evaluate:

1. CRUD TESTS:
   - Did the update operations modify the database correctly?
   - Do the before/after states show expected changes?
   - Are the query results consistent with the modifications?
   - Rate functionality as PASS/FAIL with detailed reasoning

2. ACTION TOOLS:
   - Did the meal planner provide useful meal plans?
   - Are meal suggestions relevant and practical?
   - Do new meal ideas show creativity and use specified ingredients?
   - Rate each tool as PASS/FAIL with reasoning

3. PULL TOOLS:
   - Do retrieval operations return expected data?
   - Is the information complete and accurate?
   - Are responses properly formatted?
   - Rate each tool as PASS/FAIL

4. PUSH TOOLS:
   - Do complex updates handle multiple changes correctly?
   - Are modifications applied as requested?
   - Do the tools handle edge cases appropriately?
   - Rate each tool as PASS/FAIL

PROVIDE:
- Overall system rating (PASS/FAIL)
- Individual tool ratings with explanations
- Critical issues identified
- Recommendations for improvements
- Summary of test coverage

Be thorough and specific in your analysis.
"""

async def llm_judge_evaluation(test_results: Dict[str, Any]) -> str:
    """Use LLM to evaluate test results"""
    print("Running LLM evaluation...")
    
    try:
        import openai
        client = openai.OpenAI()
        
        prompt = create_llm_judge_prompt(test_results)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert software testing judge specializing in API and database functionality testing."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"LLM judge evaluation failed: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"

# ---------------------------------------------------------------------
# Main Test Execution

async def run_all_tests() -> Dict[str, Any]:
    """Execute all test categories"""
    print("Starting comprehensive ChefByte testing...")
    start_time = datetime.now()
    
    test_results = {
        "test_info": {
            "start_time": start_time.isoformat(),
            "model": MODEL,
            "server_url": SERVER_URL
        },
        "crud_tests": await run_crud_tests(),
        "action_tools": await test_action_tools(), 
        "pull_tools": await test_pull_tools(),
        "push_tools": await test_push_tools()
    }
    
    end_time = datetime.now()
    test_results["test_info"]["end_time"] = end_time.isoformat()
    test_results["test_info"]["duration"] = str(end_time - start_time)
    
    return test_results

def main():
    """Main test execution function"""
    print("=" * 60)
    print("ChefByte MCP Server Comprehensive Test Suite")
    print("=" * 60)
    
    try:
        # Reset database to known state
        print("\n1. Resetting database to sample data...")
        reset_database()
        
        # Start MCP server
        print(f"2. Starting MCP server on port {SERVER_PORT}...")
        server_process = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT, "--port", str(SERVER_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for server to start
            time.sleep(3)
            
            # Run all tests
            print("3. Running comprehensive test suite...")
            test_results = asyncio.run(run_all_tests())
            
            # Save detailed results
            with open("chefbyte_test_results.json", "w") as f:
                json.dump(test_results, f, indent=2, default=str)
            
            # Get LLM evaluation
            print("\n4. Running LLM evaluation...")
            evaluation = asyncio.run(llm_judge_evaluation(test_results))
            
            # Display results
            print("\n" + "=" * 60)
            print("TEST RESULTS SUMMARY")
            print("=" * 60)
            print(f"Test Duration: {test_results['test_info']['duration']}")
            print(f"Model Used: {test_results['test_info']['model']}")
            
            print("\nLLM EVALUATION:")
            print("-" * 40)
            print(evaluation)
            
            # Save evaluation
            with open("chefbyte_test_evaluation.txt", "w") as f:
                f.write(f"ChefByte Test Evaluation - {datetime.now().isoformat()}\n")
                f.write("=" * 60 + "\n\n")
                f.write(evaluation)
            
            print(f"\nDetailed results saved to: chefbyte_test_results.json")
            print(f"Evaluation saved to: chefbyte_test_evaluation.txt")
            
        finally:
            # Clean up server process
            print("\n5. Shutting down MCP server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()
                
    except Exception as e:
        print(f"\nTEST SUITE FAILED: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        return 1
    
    print("\nChefByte test suite completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
