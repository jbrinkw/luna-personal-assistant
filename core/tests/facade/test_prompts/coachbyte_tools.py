import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

TESTS = [{'prompt': 'Make a plan for today: bench press 10x135 at order 1; squat 8x185 at order 2.', 'expected_tool': 'COACHBYTE_UPDATE_new_daily_plan'}, {'prompt': "What's my workout plan for today?", 'expected_tool': 'COACHBYTE_GET_today_plan'}, {'prompt': "Complete my next set; if it's squats, do 8 reps instead.", 'expected_tool': 'COACHBYTE_ACTION_complete_next_set'}, {'prompt': 'I did extra push-ups: 20 reps at bodyweight.', 'expected_tool': 'COACHBYTE_ACTION_log_completed_set'}, {'prompt': 'Add summary: Great session, felt strong on bench.', 'expected_tool': 'COACHBYTE_UPDATE_summary'}, {'prompt': 'Show my last 7 days of workouts.', 'expected_tool': 'COACHBYTE_GET_recent_history'}, {'prompt': 'Set Monday split to bench 5x at 80% 1RM and squat 10x185.', 'expected_tool': 'COACHBYTE_UPDATE_weekly_split_day'}, {'prompt': "What's my Wednesday split?", 'expected_tool': 'COACHBYTE_GET_weekly_split'}, {'prompt': 'Set a 3 minute rest timer.', 'expected_tool': 'COACHBYTE_ACTION_set_timer'}, {'prompt': 'How much time is left on my rest timer?', 'expected_tool': 'COACHBYTE_GET_timer'}]
TOOL_NAME = "CoachByte"
DEFAULT_TOOL_ROOT = os.getenv("TESTS_TOOL_ROOT", "core/tests/fakes")
DEFAULT_AGENT_PATH = os.getenv("TESTS_AGENT_PATH", "core/agent/hierarchical.py")

if __name__ == "__main__":
	from core.tests.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)
