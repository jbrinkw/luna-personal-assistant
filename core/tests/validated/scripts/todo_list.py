import sys
import os


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir))
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)


# Manually copied from tool docstrings — not imported dynamically
TESTS = [
	{
		"prompt": "List my Todoist projects.",
		"expected": '{"success": true, "count": 2, "projects": [{"id": 1, "name": "Inbox"}]}',
	},
	{
		"prompt": "List sections in project 123.",
		"expected": '{"success": true, "count": 2, "sections": [{"id": 10, "name": "Today"}]}',
	},
	{
		"prompt": "Show task 123 details.",
		"expected": '{"success": true, "task": {"id": 123, "content": "Buy groceries", "project": {"id": 1, "name": "Personal"}, "section": {"id": 2, "name": "Shopping"}}}',
	},
	{
		"prompt": "Show my tasks for today.",
		"expected": '{"success": true, "count": 2, "tasks": [{"id": 123, "content": "string", "project_id": 1, "section_id": 2, "due": {}}]}',
	},
	{
		"prompt": "Create a task: \"Add 'Buy milk' to Inbox for today\".",
		"expected": '{"success": true, "task": {"id": 123, "content": "string", "project_id": 1}}',
	},
	{
		"prompt": "Update task 123 to due tomorrow at 9am.",
		"expected": '{"success": true, "updated": true, "task_id": 123}',
	},
	{
		"prompt": "Complete task 123.",
		"expected": '{"success": true, "completed": true, "task_id": 123}',
	},
]


TOOL_NAME = "Todo List"
# Use real extensions by default
_default_tool_root = os.getenv("TESTS_TOOL_ROOT") or os.path.join(REPO_ROOT, "extensions")
_default_agent_path = os.getenv("TESTS_AGENT_PATH") or os.path.join(REPO_ROOT, "core", "agent", "hierarchical.py")
DEFAULT_TOOL_ROOT = _default_tool_root
DEFAULT_AGENT_PATH = _default_agent_path


if __name__ == "__main__":
	from core.tests.validated.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)





