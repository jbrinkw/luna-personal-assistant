import os
import sys
import subprocess
import pytest

# Ensure repo root on sys.path for imports like core.tools.test_proxy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from core.tools.test_proxy import TestRunner


@pytest.fixture(scope="session", autouse=True)
def load_sample_data():
    """
    Load CoachByte sample data once per test session so tests start from a known state.
    Uses the running Python interpreter for portability.
    """
    try:
        subprocess.run(
            [sys.executable, "extensions/coachbyte/code/python/load_sample_data.py"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        # Don't fail discovery; tests will show the error in their output if needed.
        print(f"Warning: Could not reset database - {e}. Continuing with existing data...")


def run_prompt_set(prompt_set: dict) -> dict:
    """
    Execute a single prompt set via TestRunner and return the result dict.
    Also prints output so it shows up in VS Code's test output pane.
    """
    runner = TestRunner()
    # set_index is 1-based and informational for printed output; any constant is fine
    result = runner.run_single_test_set(prompt_set, set_index=1)
    judgment = result.get("judgment", {})
    print("Judgment:", judgment)
    return result


# Define individual prompt sets (one per tool) with explicit tool instructions
PROMPT_CASES = [
    (
        "new_daily_plan",
        {
            "name": "New Daily Plan Test",
            "description": "Test adding a new daily plan set to the database using new_daily_plan tool",
            "prompts": [
                "Use the tool named exactly 'new_daily_plan' to add today's plan: bench press, 10 reps at 135 pounds as set 1. Return the tool's result.",
            ],
        },
    ),
    (
        "get_today_plan",
        {
            "name": "Get Today Plan Test",
            "description": "Test retrieving today's planned sets using get_today_plan tool",
            "prompts": [
                "Use the tool named exactly 'get_today_plan' to retrieve and show today's workout plan. Return the tool's result.",
            ],
        },
    ),
    (
        "log_completed_set",
        {
            "name": "Log Completed Set Test",
            "description": "Test logging an unplanned set with log_completed_set tool",
            "prompts": [
                "Use the tool named exactly 'log_completed_set' to log an unplanned set: 20 push-ups at bodyweight. Return the tool's result.",
            ],
        },
    ),
    (
        "complete_planned_set",
        {
            "name": "Complete Planned Set Test",
            "description": "Test marking the next planned set complete using complete_planned_set tool",
            "prompts": [
                "Use the tool named exactly 'complete_planned_set' to mark the next planned set as complete. Do not reason it yourself; call the tool and return its result.",
            ],
        },
    ),
    (
        "update_summary",
        {
            "name": "Update Summary Test",
            "description": "Test updating today's workout summary using update_summary tool",
            "prompts": [
                "Use the tool named exactly 'update_summary' to set today's summary to 'Felt strong today.'. Return the tool's result.",
            ],
        },
    ),
    (
        "get_recent_history",
        {
            "name": "Recent History Test",
            "description": "Test retrieving recent workout history using get_recent_history tool",
            "prompts": [
                "Use the tool named exactly 'get_recent_history' to show my workout history for the last 1 day. Return the tool's result.",
            ],
        },
    ),
    (
        "set_weekly_split_day",
        {
            "name": "Set Weekly Split Day Test",
            "description": "Test storing weekly split for a day using set_weekly_split_day tool",
            "prompts": [
                "Use the tool named exactly 'set_weekly_split_day' to set Monday split to bench press 5 reps at 135 pounds. Return the tool's result.",
            ],
        },
    ),
    (
        "get_weekly_split",
        {
            "name": "Get Weekly Split Test",
            "description": "Test retrieving weekly split for a day using get_weekly_split tool",
            "prompts": [
                "Use the tool named exactly 'get_weekly_split' to retrieve my split for Monday. Return the tool's result.",
            ],
        },
    ),
    (
        "set_timer",
        {
            "name": "Set Timer Test",
            "description": "Test setting a rest timer using set_timer tool",
            "prompts": [
                "Use the tool named exactly 'set_timer' to set a rest timer for 1 minute. Return the tool's result.",
            ],
        },
    ),
    (
        "get_timer",
        {
            "name": "Get Timer Test",
            "description": "Test checking timer status using get_timer tool",
            "prompts": [
                "Use the tool named exactly 'set_timer' to set a rest timer for 1 minute. Return the tool's result.",
                "Use the tool named exactly 'get_timer' to check my timer status. Return the tool's result.",
            ],
        },
    ),
]


@pytest.mark.parametrize("case_id,prompt_set", PROMPT_CASES, ids=[cid for cid, _ in PROMPT_CASES])
class TestCoachByteTools:
    def test_tool_case(self, case_id, prompt_set, load_sample_data):
        """
        Executes the tool-specific prompt set via TestRunner, then asserts that
        the LLM judge marked it as a pass. Output is printed for review in VS Code.
        """
        result = run_prompt_set(prompt_set)
        judgment = result.get("judgment", {})
        assert judgment.get("success") is True, f"LLM judgment failed for {case_id}: {judgment}"


