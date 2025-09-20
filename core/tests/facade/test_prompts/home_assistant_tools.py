import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

TESTS = [{'prompt': 'Example prompt: "list my home devices"', 'expected_tool': 'HA_GET_devices'}, {'prompt': 'Example prompt: "what\'s the status of the living room light?"', 'expected_tool': 'HA_GET_entity_status'}, {'prompt': 'Example prompt: "turn on the kitchen light"', 'expected_tool': 'HA_ACTION_turn_entity_on'}, {'prompt': 'Example prompt: "turn off the kitchen light"', 'expected_tool': 'HA_ACTION_turn_entity_off'}, {'prompt': 'Example prompt: "open spotify on my tv"', 'expected_tool': 'HA_ACTION_tv_remote'}]
TOOL_NAME = "Home Assistant"
DEFAULT_TOOL_ROOT = os.getenv("TESTS_TOOL_ROOT", "core/tests/fakes")
DEFAULT_AGENT_PATH = os.getenv("TESTS_AGENT_PATH", "core/agent/hierarchical.py")

if __name__ == "__main__":
	from core.tests.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)
