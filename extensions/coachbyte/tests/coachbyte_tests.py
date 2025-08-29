import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from core.tools.test_proxy import TestRunner
import subprocess


def main():
    """Run CoachByte tests for MCP tool coverage"""

    # Reset database with sample data (new location under extensions)
    try:
        subprocess.run([
            "python",
            "extensions/coachbyte/code/python/load_sample_data.py",
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not reset database - {e}")
        print("Continuing with tests using existing data...")

    prompt_sets = [
        {
            "name": "New Daily Plan Test",
            "description": "Test adding a new daily plan set to the database using new_daily_plan tool",
            "prompts": [
                "Use the tool named exactly 'new_daily_plan' to add today's plan: bench press, 10 reps at 135 pounds as set 1. Return the tool's result."
            ]
        },
        {
            "name": "Get Today Plan Test",
            "description": "Test retrieving today's planned sets using get_today_plan tool",
            "prompts": [
                "Use the tool named exactly 'get_today_plan' to retrieve and show today's workout plan. Return the tool's result."
            ]
        },
        {
            "name": "Log Completed Set Test",
            "description": "Test logging an unplanned set with log_completed_set tool",
            "prompts": [
                "Use the tool named exactly 'log_completed_set' to log an unplanned set: 20 push-ups at bodyweight. Return the tool's result."
            ]
        },
        {
            "name": "Complete Planned Set Test",
            "description": "Test marking the next planned set complete using complete_planned_set tool",
            "prompts": [
                "Use the tool named exactly 'complete_planned_set' to mark the next planned set as complete. Do not reason it yourself; call the tool and return its result."
            ]
        },
        {
            "name": "Update Summary Test",
            "description": "Test updating today's workout summary using update_summary tool",
            "prompts": [
                "Use the tool named exactly 'update_summary' to set today's summary to 'Felt strong today.'. Return the tool's result."
            ]
        },
        {
            "name": "Recent History Test",
            "description": "Test retrieving recent workout history using get_recent_history tool",
            "prompts": [
                "Use the tool named exactly 'get_recent_history' to show my workout history for the last 1 day. Return the tool's result."
            ]
        },
        {
            "name": "Set Weekly Split Day Test",
            "description": "Test storing weekly split for a day using set_weekly_split_day tool",
            "prompts": [
                "Use the tool named exactly 'set_weekly_split_day' to set Monday split to bench press 5 reps at 135 pounds. Return the tool's result."
            ]
        },
        {
            "name": "Get Weekly Split Test",
            "description": "Test retrieving weekly split for a day using get_weekly_split tool",
            "prompts": [
                "Use the tool named exactly 'get_weekly_split' to retrieve my split for Monday. Return the tool's result."
            ]
        },
        {
            "name": "Set Timer Test",
            "description": "Test setting a rest timer using set_timer tool",
            "prompts": [
                "Use the tool named exactly 'set_timer' to set a rest timer for 1 minute. Return the tool's result."
            ]
        },
        {
            "name": "Get Timer Test",
            "description": "Test checking timer status using get_timer tool",
            "prompts": [
                "Use the tool named exactly 'set_timer' to set a rest timer for 1 minute. Return the tool's result.",
                "Use the tool named exactly 'get_timer' to check my timer status. Return the tool's result."
            ]
        }
    ]

    runner = TestRunner()
    results = runner.run_tests(prompt_sets)
    return results


if __name__ == "__main__":
    main()


