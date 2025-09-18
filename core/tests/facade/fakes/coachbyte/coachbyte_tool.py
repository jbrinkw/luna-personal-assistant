"""Auto-generated fake tools for tests. DO NOT EDIT BY HAND."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


NAME = "CoachByte"

SYSTEM_PROMPT = """
Plan and track workouts for the user.

You can create a daily plan from a list of sets, retrieve today's plan in order,
complete the next planned set (optionally overriding reps or load), log extra
sets not in the plan, update a written summary for today, retrieve recent
history, and manage a weekly split schedule. You can also set and check a timer
for rest periods.

Tools are idempotent and validate reps/load ranges. Prefer using complete_planned_set
to advance the workout queue; use log_completed_set for unplanned sets.
"""



def COACHBYTE_UPDATE_new_daily_plan(items: 'List[Dict[str, Any]]'):
	"""Create today's daily workout plan with a list of planned sets.
Make a plan for today: bench press 10x135 at order 1; squat 8x185 at order 2.
Example Response: Planned today's workout: bench press 10x135 (order 1); squat 8x185 (order 2).
Example: {"items": [{"exercise": "string[exercise name]", "reps": int[number of reps], "load": float[weight], "rest": int[seconds], "order": int[sequence index]}]}
	"""
	return "Planned today's workout: bench press 10x135 (order 1); squat 8x185 (order 2)."


def COACHBYTE_GET_today_plan():
	"""Return today's planned workout sets in order.
What's my workout plan for today?
Example Response: Today's plan: bench press 10x135; squat 8x185.
Example: {}
	"""
	return "Today's plan: bench press 10x135; squat 8x185."


def COACHBYTE_ACTION_complete_next_set(exercise: 'Optional[str]' = None, reps: 'Optional[int]' = None, load: 'Optional[float]' = None):
	"""Complete the next planned set (optionally specify exercise and/or override reps/load).
Complete my next set; if it's squats, do 8 reps instead.
Example Response: Completed next set (squats): 8 reps.
Example: {"exercise": "string[exercise name]", "reps": int[override reps], "load": float[override load]}
	"""
	return 'Completed next set (squats): 8 reps.'


def COACHBYTE_ACTION_log_completed_set(exercise: 'str', reps: 'int', load: 'float'):
	"""Log an unplanned, completed set (not from the queue).
I did extra push-ups: 20 reps at bodyweight.
Example Response: Logged set: push-ups, 20 reps at bodyweight.
Example: {"exercise": "string[exercise name]", "reps": int[number of reps], "load": float[weight]}
	"""
	return 'Logged set: push-ups, 20 reps at bodyweight.'


def COACHBYTE_UPDATE_summary(text: 'str'):
	"""Update today's workout summary text.
Add summary: Great session, felt strong on bench.
Example Response: summary updated
Example: {"text": "string[summary text]"}
	"""
	return 'summary updated'


def COACHBYTE_GET_recent_history(days: 'int'):
	"""Get recent workout history for N days (planned vs completed).
Show my last 7 days of workouts.
Example Response: Recent 7-day workout summary returned.
Example: {"days": int[number of days]}
	"""
	return 'Recent 7-day workout summary returned.'


def COACHBYTE_UPDATE_weekly_split_day(day: 'str', items: 'List[Dict[str, Any]]'):
	"""Replace the weekly split plan for a specific day with provided sets.
Set Monday split to bench 5x at 80% 1RM and squat 10x185.
Example Response: split updated for monday with 2 sets
Usage: To specify a percent-of-1RM load, set "relative": true and pass "load" as a decimal fraction (e.g., 0.8 means 80% 1RM). For absolute loads (lbs/kg), set "relative": false (or omit) and pass a numeric load (e.g., 185).
Example: {"day": "monday", "items": [{"exercise": "bench press", "reps": 5, "load": 0.8, "relative": true, "rest": 90, "order": 1}, {"exercise": "squat", "reps": 10, "load": 185, "relative": false, "rest": 90, "order": 2}]}
	"""
	return 'split updated for monday with 2 sets'


def COACHBYTE_GET_weekly_split(day: 'Optional[str]' = None):
	"""Get weekly split plan (all days or a specific day).
What's my Wednesday split?
Example Response: Wednesday split listed.
Example: {"day": "string[day name]"}
	"""
	return 'Wednesday split listed.'


def COACHBYTE_ACTION_set_timer(minutes: 'int'):
	"""Set a rest/workout timer in minutes (1–180).
Set a 3 minute rest timer.
Example Response: Timer set for 3 minutes
Example: {"minutes": int[1-180]}
	"""
	return 'Timer set for 3 minutes'


def COACHBYTE_GET_timer():
	"""Get current timer status and remaining time.
How much time is left on my rest timer?
Example Response: {"status": "running", "remaining_seconds": 120}
Example: {}
	"""
	return '{"status": "running", "remaining_seconds": 120}'


TOOLS = [
	COACHBYTE_UPDATE_new_daily_plan,
	COACHBYTE_GET_today_plan,
	COACHBYTE_ACTION_complete_next_set,
	COACHBYTE_ACTION_log_completed_set,
	COACHBYTE_UPDATE_summary,
	COACHBYTE_GET_recent_history,
	COACHBYTE_UPDATE_weekly_split_day,
	COACHBYTE_GET_weekly_split,
	COACHBYTE_ACTION_set_timer,
	COACHBYTE_GET_timer
]
