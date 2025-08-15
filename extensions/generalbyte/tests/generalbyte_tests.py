import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from core.tools.test_proxy import TestRunner

def main():
    """Run GeneralByte tests for notifications and todo functionality"""
    
    # Define GeneralByte test prompt sets
    prompt_sets = [
        {
            "name": "Send Notification Test",
            "description": "Test sending a phone notification with title",
            "prompts": [
                "Send me a notification with title 'Test Alert' and message 'This is a test notification from GeneralByte'"
            ]
        },
        {
            "name": "Add Todo Item Test", 
            "description": "Test adding a todo item with expiration date to the todo.todo entity",
            "prompts": [
                "Add 'Buy groceries' to the todo.todo list with due date 2025-02-15"
            ]
        },
        {
            "name": "Get Todo List Test",
            "description": "Test retrieving the contents of the todo.todo list",
            "prompts": [
                "Show me my todo.todo list"
            ]
        }
    ]
    
    # Create test runner and run tests
    runner = TestRunner()
    results = runner.run_tests(prompt_sets)
    
    return results

if __name__ == "__main__":
    main() 