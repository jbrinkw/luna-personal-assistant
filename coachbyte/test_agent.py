"""
Comprehensive CoachByte MCP Server Test Suite

This test suite evaluates all CoachByte workout tracking tools using OpenAI Agents SDK 
with GPT-4.1. It tests CRUD operations on all database tables and uses LLM judging to 
evaluate functionality. The PostgreSQL database is reset to sample data before each test run.

Test Categories:
1. CRUD Tests - Test database operations for exercises, plans, completed sets, splits
2. Workout Planning Tools - Test daily plan creation and management
3. Workout Execution Tools - Test set completion and logging
4. Query Tools - Test data retrieval and workout history
5. Timer Tools - Test workout timer functionality
6. SQL Tools - Test direct database access capabilities
"""

import asyncio
import subprocess
import sys
import time
import json
import traceback
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from agents import Agent
from agents.mcp.server import MCPServerSse, MCPServerSseParams
from agents.run import Runner

# Load environment variables
load_dotenv()

import db
from load_sample_data import load_comprehensive_sample_data

SERVER_PORT = 8100
SERVER_URL = f"http://localhost:{SERVER_PORT}/sse"
SERVER_SCRIPT = "coachbyte/coachbyte_mcp_server.py"
MODEL = "gpt-4o"

# ---------------------------------------------------------------------
# Database Snapshot Functions

def get_database_snapshot(table_query: str, description: str) -> List[Dict[str, Any]]:
    """Generic function to get database table snapshot"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import db_config
        
        config = db_config.get_db_config()
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(table_query)
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return rows
        
    except Exception as e:
        print(f"Error getting {description}: {e}")
        return []

def get_exercises_snapshot() -> List[Dict[str, Any]]:
    """Get current exercises state"""
    return get_database_snapshot("SELECT * FROM exercises ORDER BY name", "exercises")

def get_daily_logs_snapshot() -> List[Dict[str, Any]]:
    """Get current daily logs state"""
    return get_database_snapshot("SELECT * FROM daily_logs ORDER BY log_date DESC", "daily logs")

def get_planned_sets_snapshot() -> List[Dict[str, Any]]:
    """Get current planned sets state"""
    return get_database_snapshot(
        """SELECT ps.*, e.name as exercise_name, dl.log_date 
           FROM planned_sets ps 
           JOIN exercises e ON ps.exercise_id = e.id 
           JOIN daily_logs dl ON ps.log_id = dl.id 
           ORDER BY dl.log_date DESC, ps.order_num""", 
        "planned sets"
    )

def get_completed_sets_snapshot() -> List[Dict[str, Any]]:
    """Get current completed sets state"""
    return get_database_snapshot(
        """SELECT cs.*, e.name as exercise_name, dl.log_date 
           FROM completed_sets cs 
           JOIN exercises e ON cs.exercise_id = e.id 
           JOIN daily_logs dl ON cs.log_id = dl.id 
           ORDER BY cs.completed_at DESC""", 
        "completed sets"
    )

def get_split_sets_snapshot() -> List[Dict[str, Any]]:
    """Get current weekly split state"""
    return get_database_snapshot(
        """SELECT ss.*, e.name as exercise_name 
           FROM split_sets ss 
           JOIN exercises e ON ss.exercise_id = e.id 
           ORDER BY ss.day_of_week, ss.order_num""", 
        "split sets"
    )

def get_today_plan_snapshot() -> List[Dict[str, Any]]:
    """Get today's specific plan"""
    today = date.today().isoformat()
    return get_database_snapshot(
        f"""SELECT ps.*, e.name as exercise_name 
            FROM planned_sets ps 
            JOIN exercises e ON ps.exercise_id = e.id 
            JOIN daily_logs dl ON ps.log_id = dl.id 
            WHERE dl.log_date = '{today}' 
            ORDER BY ps.order_num""", 
        "today's plan"
    )

# ---------------------------------------------------------------------
# Agent Interaction Functions

async def run_agent(prompt: str, timeout: int = 15) -> str:
    """Run agent with given prompt and return response"""
    server = None
    try:
        server = MCPServerSse(MCPServerSseParams(url=SERVER_URL))
        await asyncio.wait_for(server.connect(), timeout=5)
        
        agent = Agent(
            name="CoachByteTestAgent",
            instructions="""You are a comprehensive testing agent for CoachByte workout tracking tools. 
            Use the available tools to satisfy user requests. Be thorough and specific in your responses.
            When viewing data, provide detailed information about what you find. Use proper exercise names 
            and be specific about weights, reps, and sets.""",
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
# Database Reset Function

def reset_database_with_sample_data() -> bool:
    """Reset database to sample data state"""
    try:
        print("Resetting CoachByte database with sample data...")
        load_comprehensive_sample_data()
        return True
    except Exception as e:
        print(f"Failed to reset database: {e}")
        traceback.print_exc()
        return False

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
        "daily_planning": await test_crud_operation(
            "daily_planning",
            get_today_plan_snapshot,
            "Create a new daily workout plan with 3 sets of bench press at 155 lbs for 8 reps, 3 sets of squats at 185 lbs for 10 reps, and 3 sets of pull-ups bodyweight for 8 reps",
            "Show me today's complete workout plan with all exercises, weights, and reps"
        ),
        
        "set_completion": await test_crud_operation(
            "set_completion",
            get_completed_sets_snapshot,
            "I just completed my first planned set. Mark it as done with the planned weight and reps.",
            "Show me all the sets I've completed today with the weights and reps I actually did"
        ),
        
        "workout_logging": await test_crud_operation(
            "workout_logging",
            get_completed_sets_snapshot,
            "Log an additional unplanned set: 12 push-ups bodyweight that I did as a finisher",
            "Show my complete workout history for today including both planned and unplanned sets"
        ),
        
        "weekly_split": await test_crud_operation(
            "weekly_split",
            get_split_sets_snapshot,
            "Set up Monday in my weekly split with deadlifts 3 sets of 5 reps at 225 lbs, overhead press 3 sets of 8 reps at 115 lbs, and rows 3 sets of 10 reps at 135 lbs",
            "Show me my complete weekly split plan for all days"
        ),
        
        "workout_summary": await test_crud_operation(
            "workout_summary",
            get_daily_logs_snapshot,
            "Update my workout summary for today: 'Great upper body session. Felt strong on bench press, hit all target reps. Ready for legs tomorrow.'",
            "Show me the workout summaries for the past few days"
        )
    }
    
    return crud_tests

# ---------------------------------------------------------------------
# Tool-Specific Testing Functions

async def test_workout_tools() -> Dict[str, Any]:
    """Test workout-specific functionality"""
    print("Testing workout tools...")
    
    workout_tests = {
        "plan_creation": await run_agent(
            "Create a full upper body workout plan for today with bench press, rows, overhead press, and pull-ups. Use appropriate weights and rep ranges for strength training."
        ),
        
        "set_execution": await run_agent(
            "Complete the next set in my workout plan. I did the planned reps but had to reduce the weight by 10 pounds."
        ),
        
        "workout_tracking": await run_agent(
            "Show me my progress on bench press over the last week. How many sets did I complete and what weights did I use?"
        ),
        
        "split_management": await run_agent(
            "Set up a push/pull/legs split for my week. Make Tuesday push day with bench press, overhead press, and dips."
        )
    }
    
    return workout_tests

async def test_query_tools() -> Dict[str, Any]:
    """Test data retrieval and analysis tools"""
    print("Testing query tools...")
    
    query_tests = {
        "today_plan": await run_agent("What's my workout plan for today? Show all exercises with sets, reps, and weights."),
        
        "recent_history": await run_agent("Show me my workout history for the past 3 days. What exercises did I do and how did I perform?"),
        
        "weekly_split": await run_agent("What does my weekly workout split look like? Show me the plan for each day."),
        
        "exercise_analysis": await run_agent("How many total sets of squats have I done in the past week? What weights did I use?"),
        
        "sql_query": await run_agent("Run a SQL query to show me all exercises in my database ordered by name")
    }
    
    return query_tests

async def test_timer_tools() -> Dict[str, Any]:
    """Test timer functionality"""
    print("Testing timer tools...")
    
    timer_tests = {
        "set_timer": await run_agent("Set a 3-minute rest timer for my next set"),
        
        "check_timer": await run_agent("How much time is left on my timer?"),
        
        "workout_timer": await run_agent("Set a 45-minute timer for my total workout duration")
    }
    
    return timer_tests

async def test_advanced_tools() -> Dict[str, Any]:
    """Test advanced functionality and edge cases"""
    print("Testing advanced tools...")
    
    advanced_tests = {
        "complex_planning": await run_agent(
            "Create a periodized workout plan where I do 5x5 on Monday, 3x8 on Wednesday, and 4x6 on Friday, all with bench press but different weights based on percentage of my max"
        ),
        
        "workout_modification": await run_agent(
            "I need to modify today's plan. Replace squats with leg press and add calf raises at the end"
        ),
        
        "progress_tracking": await run_agent(
            "Compare my performance this week vs last week. Am I getting stronger?"
        ),
        
        "database_operations": await run_agent(
            "Use SQL to update all my bench press sets from last Monday to show I used 5 more pounds than recorded"
        )
    }
    
    return advanced_tests

# ---------------------------------------------------------------------
# LLM Judging Functions

def create_llm_judge_prompt(test_results: Dict[str, Any]) -> str:
    """Create comprehensive prompt for LLM judge"""
    return f"""
You are an expert software testing judge evaluating the functionality of CoachByte workout tracking tools.

Analyze the following test results and provide a comprehensive assessment:

TEST RESULTS:
{json.dumps(test_results, indent=2, default=str)}

For each test category, evaluate:

1. CRUD TESTS:
   - Did workout plan creation work correctly?
   - Were set completions recorded properly?
   - Did workout logging capture the right data?
   - Was weekly split configuration successful?
   - Were workout summaries updated correctly?
   - Rate functionality as PASS/FAIL with detailed reasoning

2. WORKOUT TOOLS:
   - Did plan creation generate appropriate workout plans?
   - Was set execution handled correctly with modifications?
   - Did workout tracking provide accurate progress information?
   - Was split management functional?
   - Rate each tool as PASS/FAIL with reasoning

3. QUERY TOOLS:
   - Did data retrieval return expected workout information?
   - Was exercise analysis accurate and complete?
   - Did SQL queries execute properly?
   - Were historical data queries working?
   - Rate each tool as PASS/FAIL

4. TIMER TOOLS:
   - Did timer setting work correctly?
   - Was timer status checking functional?
   - Did different timer durations work as expected?
   - Rate timer functionality as PASS/FAIL

5. ADVANCED TOOLS:
   - Did complex planning handle multiple parameters?
   - Were workout modifications applied correctly?
   - Did progress tracking provide meaningful insights?
   - Were database operations executed safely?
   - Rate advanced functionality as PASS/FAIL

PROVIDE:
- Overall system rating (PASS/FAIL)
- Individual tool ratings with explanations
- Critical issues identified
- Recommendations for improvements
- Assessment of database integrity
- Summary of test coverage

Be thorough and specific in your analysis, considering workout tracking best practices.
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
                {"role": "system", "content": "You are an expert software testing judge specializing in fitness and workout tracking applications."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"LLM judge evaluation failed: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"

# ---------------------------------------------------------------------
# Main Test Execution

async def run_all_tests() -> Dict[str, Any]:
    """Execute all test categories"""
    print("Starting comprehensive CoachByte testing...")
    start_time = datetime.now()
    
    test_results = {
        "test_info": {
            "start_time": start_time.isoformat(),
            "model": MODEL,
            "server_url": SERVER_URL
        },
        "crud_tests": await run_crud_tests(),
        "workout_tools": await test_workout_tools(),
        "query_tools": await test_query_tools(),
        "timer_tools": await test_timer_tools(),
        "advanced_tools": await test_advanced_tools()
    }
    
    end_time = datetime.now()
    test_results["test_info"]["end_time"] = end_time.isoformat()
    test_results["test_info"]["duration"] = str(end_time - start_time)
    
    return test_results

def main():
    """Main test execution function"""
    print("=" * 60)
    print("CoachByte MCP Server Comprehensive Test Suite")
    print("=" * 60)
    
    try:
        # Reset database to known state
        print("\n1. Resetting database to sample data...")
        if not reset_database_with_sample_data():
            print("Failed to reset database. Exiting...")
            return 1
        
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
            with open("coachbyte_test_results.json", "w") as f:
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
            with open("coachbyte_test_evaluation.txt", "w") as f:
                f.write(f"CoachByte Test Evaluation - {datetime.now().isoformat()}\n")
                f.write("=" * 60 + "\n\n")
                f.write(evaluation)
            
            print(f"\nDetailed results saved to: coachbyte_test_results.json")
            print(f"Evaluation saved to: coachbyte_test_evaluation.txt")
            
        except Exception as e:
            print(f"\nTEST SUITE FAILED: {str(e)}")
            print("\nFull traceback:")
            traceback.print_exc()
            return 1
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
    
    print("\nCoachByte test suite completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
