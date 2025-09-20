import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

TESTS = [{'prompt': 'Show my tasks for today.', 'expected_tool': 'TODOLIST_GET_list_tasks'}, {'prompt': 'Create a task: "Add \'Buy milk\' to Inbox for today".', 'expected_tool': 'TODOLIST_ACTION_create_task'}, {'prompt': 'Update task 123 to due tomorrow at 9am.', 'expected_tool': 'TODOLIST_UPDATE_update_task'}, {'prompt': 'Complete task 123.', 'expected_tool': 'TODOLIST_ACTION_complete_task'}]
TOOL_NAME = "Todo List"
DEFAULT_TOOL_ROOT = os.getenv("TESTS_TOOL_ROOT", "core/tests/fakes")
DEFAULT_AGENT_PATH = os.getenv("TESTS_AGENT_PATH", "core/agent/hierarchical.py")

if __name__ == "__main__":
	from core.tests.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)
