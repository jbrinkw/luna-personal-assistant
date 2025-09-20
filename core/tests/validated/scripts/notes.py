import sys
import os


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir))
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)


# Manually copied from tool docstrings — not imported dynamically
TESTS = [
	{
		"prompt": "show my project hierarchy",
		"expected": '"Eco AI\n- Roadmap\n- Research"',
	},
	{
		"prompt": "show the text for project Eco AI",
		"expected": '{"project_id": "Eco AI", "root_page_path": "...", "root_page_text": "# Eco AI ...", "note_page_path": "...", "note_page_text": "..."}',
	},
	{
		"prompt": "find my notes between 06/01/24 and 06/15/24",
		"expected": '{"start_date": "06/01/24", "end_date": "06/15/24", "entries": [{"file": "...Notes.md", "date": "2024-06-01", "date_str": "6/1/24", "content": "..."}]}',
	},
	{
		"prompt": "add 'ship MVP' under 'Milestones' for project Eco AI",
		"expected": '{"project_id": "Eco AI", "note_file": ".../Notes.md", "created_file": false, "created_entry": true, "appended": true, "date_str": "6/1/24"}',
	},
]


TOOL_NAME = "Notes"
# Use real extensions by default
_default_tool_root = os.getenv("TESTS_TOOL_ROOT") or os.path.join(REPO_ROOT, "extensions")
_default_agent_path = os.getenv("TESTS_AGENT_PATH") or os.path.join(REPO_ROOT, "core", "agent", "parallel_agent.py")
DEFAULT_TOOL_ROOT = _default_tool_root
DEFAULT_AGENT_PATH = _default_agent_path


if __name__ == "__main__":
	from core.tests.validated.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)





