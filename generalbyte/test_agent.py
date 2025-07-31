"""
Comprehensive GeneralByte MCP Server Test Suite

This test suite evaluates all GeneralByte Home Assistant integration tools using 
OpenAI Agents SDK with GPT-4.1. It tests notification sending and todo list 
management functionality. Since GeneralByte doesn't have a database, tests focus 
on functional integration with Home Assistant services.

Test Categories:
1. Notification Tests - Test phone notification sending with various messages
2. Todo List Tests - Test todo list retrieval and management
3. Todo CRUD Tests - Test creating, updating, and deleting todo items
4. Integration Tests - Test complex scenarios combining multiple tools
5. Error Handling Tests - Test behavior with invalid inputs or service failures
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

SERVER_PORT = 8050
SERVER_URL = f"http://localhost:{SERVER_PORT}/sse"
SERVER_SCRIPT = "generalbyte/generalbyte_mcp_server.py"
MODEL = "gpt-4o"
load_dotenv()

# ---------------------------------------------------------------------
# Agent Interaction Functions

async def run_agent(prompt: str, timeout: int = 15) -> str:
    """Run agent with given prompt and return response"""
    server = None
    try:
        server = MCPServerSse(MCPServerSseParams(url=SERVER_URL))
        await asyncio.wait_for(server.connect(), timeout=5)
        
        agent = Agent(
            name="GeneralByteTestAgent",
            instructions="""You are a comprehensive testing agent for GeneralByte Home Assistant tools. 
            Use the available tools to satisfy user requests. Be thorough and specific in your responses.
            When testing notifications, use appropriate messages. When working with todo lists, be specific about items.""",
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
# Test Categories

async def test_notification_functionality() -> Dict[str, Any]:
    """Test notification sending functionality"""
    print("Testing notification functionality...")
    
    notification_tests = {
        "basic_notification": await run_agent(
            "Send a test notification with the message 'GeneralByte test suite is running' and title 'Test Alert'"
        ),
        
        "custom_notification": await run_agent(
            "Send me a notification that says 'Your workout reminder: Time for chest and arms!'"
        )
    }
    
    return notification_tests

async def test_todo_list_functionality() -> Dict[str, Any]:
    """Test todo list retrieval and management"""
    print("Testing todo list functionality...")
    
    todo_tests = {
        "view_todo_list": await run_agent(
            "Show me my complete todo list with all items and their status"
        ),
        
        "todo_summary": await run_agent(
            "Give me a summary of my todo list - how many items total and how many are completed vs pending"
        )
    }
    
    return todo_tests

async def test_todo_crud_operations() -> Dict[str, Any]:
    """Test creating, updating, and deleting todo items"""
    print("Testing todo CRUD operations...")
    
    # Store initial state for comparison
    initial_state = await run_agent("Show me my current todo list")
    
    crud_tests = {
        "initial_state": initial_state,
        
        "create_todo_item": await run_agent(
            "Create a new todo item: 'Test GeneralByte MCP integration'"
        ),
        
        "state_after_creation": await run_agent(
            "Show me my updated todo list after adding the new item"
        ),
        
        "update_todo_status": await run_agent(
            "Mark the GeneralByte MCP integration test item as completed"
        ),
        
        "final_state": await run_agent(
            "Show me my final todo list after the modifications"
        )
    }
    
    return crud_tests

async def test_integration_scenarios() -> Dict[str, Any]:
    """Test complex scenarios combining multiple tools"""
    print("Testing integration scenarios...")
    
    integration_tests = {
        "todo_with_notification": await run_agent(
            "Create a todo item 'Review quarterly reports' and then send me a notification to remind me about it"
        )
    }
    
    return integration_tests

async def test_error_handling() -> Dict[str, Any]:
    """Test error handling and edge cases"""
    print("Testing error handling...")
    
    error_tests = {
        "invalid_todo_operation": await run_agent(
            "Delete a todo item that doesn't exist called 'Nonexistent Item'"
        )
    }
    
    return error_tests

async def test_home_assistant_connectivity() -> Dict[str, Any]:
    """Test Home Assistant service connectivity and configuration"""
    print("Testing Home Assistant connectivity...")
    
    connectivity_tests = {
        "service_status": await run_agent(
            "Test if the Home Assistant connection is working by sending a simple 'Connection test' notification"
        )
    }
    
    return connectivity_tests

async def cleanup_test_data() -> Dict[str, Any]:
    """Clean up test data created during tests"""
    print("Cleaning up test data...")
    
    cleanup_results = {
        "clear_test_todos": await run_agent(
            "Delete all todo items that contain 'Test', 'GeneralByte', 'MCP', 'integration', or 'quarterly reports' to clean up test data"
        ),
        
        "final_cleanup_check": await run_agent(
            "Show me the final todo list after cleanup"
        )
    }
    
    return cleanup_results

# ---------------------------------------------------------------------
# LLM Judging Functions

def create_llm_judge_prompt(test_results: Dict[str, Any]) -> str:
    """Create comprehensive prompt for LLM judge"""
    return f"""
You are an expert software testing judge evaluating the functionality of GeneralByte Home Assistant integration tools.

Analyze the following test results and provide a comprehensive assessment:

TEST RESULTS:
{json.dumps(test_results, indent=2, default=str)}

For each test category, evaluate:

1. NOTIFICATION TESTS:
   - Did notification sending work correctly?
   - Were different notification types handled properly?
   - Did custom messages and titles work as expected?
   - Were notifications delivered successfully?
   - Rate functionality as PASS/FAIL with detailed reasoning

2. TODO LIST TESTS:
   - Did todo list retrieval work correctly?
   - Was todo data displayed accurately?
   - Were filtering and search operations functional?
   - Did status checking work properly?
   - Rate each operation as PASS/FAIL with reasoning

3. TODO CRUD TESTS:
   - Did todo item creation work correctly?
   - Were todo updates applied successfully?
   - Did todo deletion function properly?
   - Was the before/after state tracking accurate?
   - Rate CRUD functionality as PASS/FAIL

4. INTEGRATION TESTS:
   - Did combined operations work smoothly?
   - Were complex workflows handled correctly?
   - Did multi-step scenarios complete successfully?
   - Was data consistency maintained across operations?
   - Rate integration as PASS/FAIL

5. ERROR HANDLING TESTS:
   - Were error conditions handled gracefully?
   - Did invalid operations return appropriate responses?
   - Were edge cases managed correctly?
   - Did the system remain stable during error conditions?
   - Rate error handling as PASS/FAIL

6. CONNECTIVITY TESTS:
   - Did Home Assistant connection work properly?
   - Were services accessible and responsive?
   - Did configuration settings work correctly?
   - Were authentication and authorization handled properly?
   - Rate connectivity as PASS/FAIL

PROVIDE:
- Overall system rating (PASS/FAIL)  
- Individual tool ratings with explanations
- Critical issues identified
- Home Assistant integration assessment
- Recommendations for improvements
- Summary of test coverage
- Assessment of tool reliability and user experience

Be thorough and specific in your analysis, considering Home Assistant integration best practices.
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
                {"role": "system", "content": "You are an expert software testing judge specializing in home automation and notification systems."},
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
    print("Starting comprehensive GeneralByte testing...")
    start_time = datetime.now()
    
    test_results = {
        "test_info": {
            "start_time": start_time.isoformat(),
            "model": MODEL,
            "server_url": SERVER_URL
        },
        "notification_tests": await test_notification_functionality(),
        "todo_list_tests": await test_todo_list_functionality(),
        "todo_crud_tests": await test_todo_crud_operations(),
        "integration_tests": await test_integration_scenarios(),
        "error_handling_tests": await test_error_handling(),
        "connectivity_tests": await test_home_assistant_connectivity(),
        "cleanup": await cleanup_test_data()
    }
    
    end_time = datetime.now()
    test_results["test_info"]["end_time"] = end_time.isoformat()
    test_results["test_info"]["duration"] = str(end_time - start_time)
    
    return test_results

def main():
    """Main test execution function"""
    print("=" * 60)
    print("GeneralByte MCP Server Comprehensive Test Suite")
    print("=" * 60)
    
    try:
        # Start MCP server
        print(f"1. Starting MCP server on port {SERVER_PORT}...")
        server_process = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT, "--port", str(SERVER_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for server to start
            time.sleep(2)
            
            # Run all tests
            print("2. Running comprehensive test suite...")
            test_results = asyncio.run(run_all_tests())
            
            # Save detailed results
            with open("generalbyte_test_results.json", "w") as f:
                json.dump(test_results, f, indent=2, default=str)
            
            # Get LLM evaluation
            print("\n3. Running LLM evaluation...")
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
            with open("generalbyte_test_evaluation.txt", "w") as f:
                f.write(f"GeneralByte Test Evaluation - {datetime.now().isoformat()}\n")
                f.write("=" * 60 + "\n\n")
                f.write(evaluation)
            
            print(f"\nDetailed results saved to: generalbyte_test_results.json")
            print(f"Evaluation saved to: generalbyte_test_evaluation.txt")
            
        finally:
            # Clean up server process
            print("\n4. Shutting down MCP server...")
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
    
    print("\nGeneralByte test suite completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
