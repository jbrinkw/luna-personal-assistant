import sys
import os


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir))
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)


# Seed sample data for CoachByte DB before running tests
try:
	from extensions.coachbyte.code.python.load_sample_data import load_comprehensive_sample_data
	# This function creates tables if missing and loads sample rows
	load_comprehensive_sample_data()
except Exception as e:
	print(f"[coachbyte seed] warning: {e}")


# Manually copied from tool docstrings — not imported dynamically
TESTS = [
	{
		"prompt": "Make a plan for today: bench press 10x135 at order 1; squat 8x185 at order 2.",
		"expected": "Planned today's workout: bench press 10x135 (order 1); squat 8x185 (order 2).",
	},
	{
		"prompt": "What's my workout plan for today?",
		"expected": "Today's plan: bench press 10x135; squat 8x185.",
	},
	{
		"prompt": "Complete my next set; if it's squats, do 8 reps instead.",
		"expected": "Completed next set (squats): 8 reps.",
	},
	{
		"prompt": "I did extra push-ups: 20 reps at bodyweight.",
		"expected": "Logged set: push-ups, 20 reps at bodyweight.",
	},
	{
		"prompt": "Add summary: Great session, felt strong on bench.",
		"expected": "summary updated",
	},
	{
		"prompt": "Show my last 7 days of workouts.",
		"expected": "Recent 7-day workout summary returned.",
	},
	{
		"prompt": "Set Monday split to bench 5x at 80% 1RM and squat 10x185.",
		"expected": "split updated for monday with 2 sets",
	},
	{
		"prompt": "What's my Wednesday split?",
		"expected": "Wednesday split listed.",
	},
	{
		"prompt": "Set a 3 minute rest timer.",
		"expected": "Timer set for 3 minutes",
	},
	{
		"prompt": "How much time is left on my rest timer?",
		"expected": '{"status": "running", "remaining_seconds": 120}',
	},
]


TOOL_NAME = "CoachByte"
# Normalize to absolute defaults for direct execution
# Use real extensions by default (tests validate real tools); can override via TESTS_TOOL_ROOT
_default_tool_root = os.getenv("TESTS_TOOL_ROOT") or os.path.join(REPO_ROOT, "extensions")
_default_agent_path = os.getenv("TESTS_AGENT_PATH") or os.path.join(REPO_ROOT, "core", "agent", "parallel_agent.py")
DEFAULT_TOOL_ROOT = _default_tool_root
DEFAULT_AGENT_PATH = _default_agent_path


if __name__ == "__main__":
	from core.tests.validated.runner import run_tests
	run_tests(agent_path=DEFAULT_AGENT_PATH, tool_root=DEFAULT_TOOL_ROOT, tests=TESTS, tool_name=TOOL_NAME)


