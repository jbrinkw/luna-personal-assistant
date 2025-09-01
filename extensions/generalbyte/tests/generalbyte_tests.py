import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from core.tools.test_proxy import TestRunner

def main():
    """Run GeneralByte tests for notifications and todo functionality"""
    
    # Define GeneralByte test prompt sets
    prompt_sets = [
        {
            "name": "Send Notification Test",
            "description": "Test sending a phone notification using GENERAL_ACTION_send_phone_notification tool",
            "prompts": [
                "Use the tool named exactly 'GENERAL_ACTION_send_phone_notification' to send a notification with title 'Test Alert' and message 'This is a test notification from GeneralByte'. Return the tool's result."
            ]
        },
        {
            "name": "Add Todo Item Test", 
            "description": "Test adding a todo item via GENERAL_ACTION_modify_todo_item tool",
            "prompts": [
                "Use the tool named exactly 'GENERAL_ACTION_modify_todo_item' with action 'create' to add 'Buy groceries' to entity_id 'todo.todo' with due_date '2025-02-15'. Return the tool's result."
            ]
        },
        {
            "name": "Get Todo List Test",
            "description": "Test retrieving the contents of the todo.todo list using GENERAL_GET_todo_list tool",
            "prompts": [
                "Use the tool named exactly 'GENERAL_GET_todo_list' to retrieve the items in entity_id 'todo.todo'. Return the tool's result."
            ]
        }
    ]
    
    # Create test runner and run tests
    runner = TestRunner()
    results = runner.run_tests(prompt_sets)
    
    return results

if __name__ == "__main__":
    main() 