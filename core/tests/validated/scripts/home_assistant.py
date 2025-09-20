import sys
import os


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir))
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)


# Manually copied from tool docstrings — not imported dynamically
TESTS = [
	{
		"prompt": "list my home devices",
		"expected": '{"devices": [{"entity_id": "light.kitchen", "domain": "light", "state": "off", "friendly_name": "Kitchen Light"}]}',
	},
	{
		"prompt": "what's the status of the living room light?",
		"expected": '{"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 200}}',
	},
	{
		"prompt": "turn on the kitchen light",
		"expected": "{\"success\": true, \"message\": \"Successfully turned on 'light.kitchen'\"}",
	},
	{
		"prompt": "turn off the kitchen light",
		"expected": "{\"success\": true, \"message\": \"Successfully turned off 'light.kitchen'\"}",
	},
	{
		"prompt": "open spotify on my tv",
		"expected": "{\"success\": true, \"message\": \"Sent 'open spotify' to remote.living_room_tv\"}",
	},
]


TOOL_NAME = "Home Assistant"
# Use real extensions by default (tests validate real tools); can override via TESTS_TOOL_ROOT
_default_tool_root = os.getenv("TESTS_TOOL_ROOT") or os.path.join(REPO_ROOT, "extensions")
_default_agent_path = os.getenv("TESTS_AGENT_PATH") or os.path.join(REPO_ROOT, "core", "agent", "hierarchical.py")
DEFAULT_TOOL_ROOT = _default_tool_root
DEFAULT_AGENT_PATH = _default_agent_path


if __name__ == "__main__":
	from core.tests.validated.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)





