# CoachByte Agent

This document explains the behaviour of the Python agent that powers the workout tracker.

## Purpose
The agent uses the OpenAI Agents SDK to translate natural language requests into structured database actions.  It connects to PostgreSQL and exposes a collection of tools for workout planning and tracking.

## Available Tools
- **new_daily_plan** – create today’s workout plan from a list of sets.
- **get_today_plan** – show the current plan in order.
- **complete_planned_set** – mark the next planned set as completed, optionally overriding reps or load.
- **log_completed_set** – record an extra set that was not in the plan.
- **update_summary** – save a text summary of the workout day.
- **get_recent_history** – retrieve workouts for the last N days.
- **set_weekly_split_day/get_weekly_split** – store and fetch a weekly template.
- **run_sql/arbitrary_update** – execute custom SQL when needed.
- **set_timer/get_timer** – manage rest timers between sets.

The agent stitches recent summaries and personal-record data into its system prompt so that it can give contextually aware answers.

## How It Is Invoked
`server.js` exposes a `/api/chat` endpoint.  Incoming chat messages are written to a temporary JSON file and processed by `chat_agent.py`, which loads recent conversation history, runs the agent and returns the assistant’s reply.  Replies are saved back to the chat memory table for context in future requests.

Developers can also call `run_agent()` directly from Python for scripted interactions or tests.

