import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

TESTS = [{'prompt': 'search for langchain tavily integration".', 'expected_tool': 'GENERAL_ACTION_send_phone_notification'}, {'prompt': 'Example: "search for langchain tavily integration"', 'expected_tool': 'GENERAL_GET_web_search'}, {'prompt': 'Example: "weather in Paris" or just call without arguments for Charlotte.', 'expected_tool': 'GENERAL_GET_weather'}]
TOOL_NAME = "GeneralByte"
DEFAULT_TOOL_ROOT = os.getenv("TESTS_TOOL_ROOT", "core/tests/fakes")
DEFAULT_AGENT_PATH = os.getenv("TESTS_AGENT_PATH", "core/agent/parallel_agent.py")

if __name__ == "__main__":
	from core.tests.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)
