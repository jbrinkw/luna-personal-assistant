# CoachByte — User Guide

## Purpose
Plan and track workouts: build daily plans, complete planned sets (with overrides), log extra sets, manage a weekly split, and use rest timers.

## Tools

### `COACHBYTE_UPDATE_new_daily_plan`
- Summary: Create today's daily workout plan with a list of planned sets.
- Example Prompt: Make a plan for today: bench press 10x135 at order 1; squat 8x185 at order 2.
- Example Args: {"items": [{"exercise": "string", "reps": int, "load": float, "rest": int, "order": int}]}
- Returns: summary of planned sets.

### `COACHBYTE_GET_today_plan`
- Summary: Return today's planned workout sets in order.
- Example Prompt: What's my workout plan for today?
- Example Args: {}
- Returns: list of planned sets with exercise, reps, load, rest, order.

### `COACHBYTE_ACTION_complete_next_set`
- Summary: Complete the next planned set (optionally specify exercise and/or override reps/load).
- Example Prompt: Complete my next set; if it's squats, do 8 reps instead.
- Example Args: {"exercise": "string", "reps": int, "load": float}
- Returns: confirmation string; sets a rest timer when available.

### `COACHBYTE_ACTION_log_completed_set`
- Summary: Log an unplanned, completed set.
- Example Prompt: I did extra push-ups: 20 reps at bodyweight.
- Example Args: {"exercise": "string", "reps": int, "load": float}
- Returns: confirmation string.

### `COACHBYTE_UPDATE_summary`
- Summary: Update today's workout summary text.
- Example Prompt: Add summary: Great session, felt strong on bench.
- Example Args: {"text": "string"}
- Returns: "summary updated".

### `COACHBYTE_GET_recent_history`
- Summary: Get recent workout history for N days (planned vs completed).
- Example Prompt: Show my last 7 days of workouts.
- Example Args: {"days": int}
- Returns: list of historical entries.

### `COACHBYTE_UPDATE_weekly_split_day`
- Summary: Replace the weekly split plan for a specific day with provided sets.
- Example Prompt: Set Monday split to bench 5x at 80% 1RM and squat 10x185.
- Example Args: {"day": "monday", "items": [{"exercise": "string", "reps": int, "load": number, "relative": bool, "rest": int, "order": int}]}
- Returns: confirmation string.

### `COACHBYTE_GET_weekly_split`
- Summary: Get weekly split plan (all days or a specific day).
- Example Prompt: What's my Wednesday split?
- Example Args: {"day": "string[day name]"}
- Returns: list of split sets.

### `COACHBYTE_ACTION_set_timer`
- Summary: Set a rest/workout timer in minutes (1–180).
- Example Prompt: Set a 3 minute rest timer.
- Example Args: {"minutes": int}
- Returns: confirmation or error.

### `COACHBYTE_GET_timer`
- Summary: Get current timer status and remaining time.
- Example Prompt: How much time is left on my rest timer?
- Example Args: {}
- Returns: {"status": "running|no_timer|error", "remaining_seconds": number}
