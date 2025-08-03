from test_proxy import TestRunner
import subprocess

def main():
    """Run CoachByte tests for MCP tool coverage"""

    # Reset database with sample data
    subprocess.run(["python", "coachbyte/load_sample_data.py"], check=True)

    prompt_sets = [
        {
            "name": "New Daily Plan Test",
            "description": "Test adding a new daily plan set to the database using new_daily_plan tool",
            "prompts": [
                "Plan bench press 10 reps at 135 pounds as set 1 for today."
            ]
        },
        {
            "name": "Get Today Plan Test",
            "description": "Test retrieving today's planned sets using get_today_plan tool",
            "prompts": [
                "Plan bench press 10 reps at 135 pounds as set 1 for today.",
                "What is today’s workout plan?"
            ]
        },
        {
            "name": "Log Completed Set Test",
            "description": "Test logging an unplanned set with log_completed_set tool",
            "prompts": [
                "Log 20 push-ups at bodyweight."
            ]
        },
        {
            "name": "Complete Planned Set Test",
            "description": "Test marking the next planned set complete using complete_planned_set tool",
            "prompts": [
                "Plan bench press 10 reps at 135 pounds as set 1 for today.",
                "Complete the next set."
            ]
        },
        {
            "name": "Update Summary Test",
            "description": "Test updating today's workout summary using update_summary tool",
            "prompts": [
                "Update today’s summary to 'Felt strong today.'"
            ]
        },
        {
            "name": "Recent History Test",
            "description": "Test retrieving recent workout history using get_recent_history tool",
            "prompts": [
                "Plan bench press 10 reps at 135 pounds as set 1 for today.",
                "Complete the next set.",
                "Show my workout history for the last 1 day."
            ]
        },
        {
            "name": "Set Weekly Split Day Test",
            "description": "Test storing weekly split for a day using set_weekly_split_day tool",
            "prompts": [
                "Set Monday split to bench press 5 reps at 135 pounds."
            ]
        },
        {
            "name": "Get Weekly Split Test",
            "description": "Test retrieving weekly split for a day using get_weekly_split tool",
            "prompts": [
                "What is my split for Monday?"
            ]
        },
        {
            "name": "Set Timer Test",
            "description": "Test setting a rest timer using set_timer tool",
            "prompts": [
                "Set a rest timer for 1 minute."
            ]
        },
        {
            "name": "Get Timer Test",
            "description": "Test checking timer status using get_timer tool",
            "prompts": [
                "Set a rest timer for 1 minute.",
                "Check my timer."
            ]
        }
    ]

    runner = TestRunner()
    results = runner.run_tests(prompt_sets)
    return results

if __name__ == "__main__":
    main()
