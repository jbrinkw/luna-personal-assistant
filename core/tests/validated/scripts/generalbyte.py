import sys
import os


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir))
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)


# Manually copied from tool docstrings — not imported dynamically
TESTS = [
	{
		"prompt": 'Notify me: "Garage door is open".',
		"expected": '{"success": true, "message": "Notification sent"}',
	},
	{
		"prompt": "search for langchain tavily integration",
		"expected": '{"query": "...", "answer": null, "results": [{"title": "...", "url": "...", "content": "..."}], "images": []}',
	},
	{
		"prompt": 'weather in Paris',
		"expected": '{"location_query": "Paris", "resolved_name": "Paris, Île-de-France, France", "current": {"temperature_c": 21.5, "weather_description": "Clear sky"}}',
	},
]


TOOL_NAME = "GeneralByte"
# Use real extensions by default
_default_tool_root = os.getenv("TESTS_TOOL_ROOT") or os.path.join(REPO_ROOT, "extensions")
_default_agent_path = os.getenv("TESTS_AGENT_PATH") or os.path.join(REPO_ROOT, "core", "agent", "parallel_agent.py")
DEFAULT_TOOL_ROOT = _default_tool_root
DEFAULT_AGENT_PATH = _default_agent_path


if __name__ == "__main__":
	from core.tests.validated.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)





