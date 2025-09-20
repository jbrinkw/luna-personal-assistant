import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

TESTS = [{'prompt': 'Example: "show my project hierarchy"', 'expected_tool': 'NOTES_GET_project_hierarchy'}, {'prompt': 'Example: "show the text for project Eco AI"', 'expected_tool': 'NOTES_GET_project_text'}, {'prompt': 'Example: "find my notes between 06/01/24 and 06/15/24"', 'expected_tool': 'NOTES_GET_notes_by_date_range'}, {'prompt': 'Example: "add \'ship MVP\' under \'Milestones\' for project Eco AI"', 'expected_tool': 'NOTES_UPDATE_project_note'}]
TOOL_NAME = "Notes"
DEFAULT_TOOL_ROOT = os.getenv("TESTS_TOOL_ROOT", "core/tests/fakes")
DEFAULT_AGENT_PATH = os.getenv("TESTS_AGENT_PATH", "core/agent/hierarchical.py")

if __name__ == "__main__":
	from core.tests.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)
