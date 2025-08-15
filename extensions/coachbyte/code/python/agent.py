import os
from typing import List
from datetime import datetime, timezone

from agents import Agent, Runner

import agent_tools as tools
from db import get_connection
import psycopg2.extras

# Use environment variable OPENAI_API_KEY by default

MODEL = os.environ.get("OPENAI_MODEL", "o3")

def get_corrected_time():
    """Get the current UTC time"""
    return datetime.now(timezone.utc)

def get_timestamp():
    """Get current UTC timestamp in readable format"""
    return get_corrected_time().strftime("[%Y-%m-%d %H:%M:%S]")

def get_recent_daily_summaries():
    """Get the most recent 5 daily summaries"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT log_date, summary 
            FROM daily_logs 
            WHERE summary IS NOT NULL AND summary != '' 
            ORDER BY log_date DESC 
            LIMIT 5
        """)
        summaries = cur.fetchall()
        conn.close()
        return summaries
    except Exception as e:
        print(f"Error fetching daily summaries: {e}")
        return []

def get_current_prs():
    """Return current tracked personal-record data for tracked exercises."""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get tracked exercises from database instead of hardcoded list
        cur.execute("SELECT exercise FROM tracked_exercises ORDER BY exercise")
        tracked_rows = cur.fetchall()
        tracked_exercises = [row['exercise'] for row in tracked_rows]
        
        if not tracked_exercises:
            return {}  # No exercises being tracked

        cur.execute(
            """
            SELECT e.name AS exercise,
                   cs.reps_done,
                   MAX(cs.load_done) AS max_load
            FROM completed_sets cs
            JOIN exercises e ON cs.exercise_id = e.id
            WHERE e.name = ANY(%s)
              AND cs.reps_done > 0
              AND cs.load_done > 0
            GROUP BY e.name, cs.reps_done
            ORDER BY e.name, cs.reps_done
            """,
            (tracked_exercises,),
        )

        rows = cur.fetchall()
        conn.close()

        prs: dict[str, list[dict]] = {}
        for row in rows:
            prs.setdefault(row["exercise"], []).append(
                {"reps": row["reps_done"], "maxLoad": row["max_load"]}
            )
        return prs
    except Exception as e:
        print(f"Error fetching PRs: {e}")
        return {}

def create_dynamic_context():
    """Create dynamic context with recent summaries and PRs"""
    context_parts = []
    
    # Add recent daily summaries
    summaries = get_recent_daily_summaries()
    if summaries:
        context_parts.append("RECENT DAILY SUMMARIES:")
        for summary in summaries:
            context_parts.append(f"  {summary['log_date']}: {summary['summary']}")
        context_parts.append("")
    
    # Add current PRs
    prs = get_current_prs()
    if prs:
        context_parts.append("CURRENT TRACKED PERSONAL RECORDS:")
        for exercise, pr_list in prs.items():
            pr_strings = [f"{pr['reps']} rep{'s' if pr['reps'] != 1 else ''}: {pr['maxLoad']} lbs" for pr in pr_list]
            context_parts.append(f"  {exercise}: {', '.join(pr_strings)}")
        context_parts.append("")
    
    return "\n".join(context_parts)

def create_agent() -> Agent:
    """Return a CoachByte agent configured with available tools."""
    
    # Get dynamic context (recent summaries and PRs)
    dynamic_context = create_dynamic_context()
    
    # Build the full instructions with context first
    base_instructions = "You are CoachByte, a fitness tracking assistant that helps manage workout plans and logs. "
    
    if dynamic_context:
        full_instructions = dynamic_context + "\n" + base_instructions
    else:
        full_instructions = base_instructions
    
    return Agent(
        name="CoachByte",
        instructions=(
            full_instructions +
            "\n\nKey capabilities:"
            "\n- Create and modify workout plans using new_daily_plan (each set includes exercise, reps, load, rest time in seconds, and order)"
            "\n- Log completed exercises using log_completed_set"
            "\n- Complete planned sets using complete_planned_set (finds next set in queue, can override planned reps/load values)"
            "\n- Track progress using get_recent_history"
            "\n- Query workout data using run_sql"
            "\n- Update workout summaries using update_summary"
            "\n- Make database modifications using arbitrary_update"
            "\n- Set workout timers using set_timer (specify duration in minutes)"
            "\n- Check timer status using get_timer"
            "\n\nImportant workflow guidelines:"
            "\n- When a user says they 'completed a set', 'finished a set', 'did a set', or similar, ALWAYS use complete_planned_set (NOT log_completed_set)"
            "\n- complete_planned_set finds the next planned set in the queue and completes it properly"
            "\n- NEVER use log_completed_set when completing planned sets - it bypasses the queue system"
            "\n- Only use log_completed_set for unplanned/extra sets that weren't in the original plan"
            "\n- The complete_planned_set tool will automatically find the next planned set and handle cases where none exist"
            "\n- Do NOT check for planned sets manually when the user indicates they completed one - let the tool handle it"
            "\n- If complete_planned_set says no sets are available, then offer to create a new plan"
            "\n\nMemory and Context:"
            "\n- You have access to previous conversation history. Use this to remember user preferences, names, and context."
            "\n- If someone tells you their name, remember it and use it in future responses."
            "\n- Maintain conversation continuity - reference previous topics and responses when relevant."
            "\n- If asked about previous conversations, refer to the context provided."
            "\n\nImportant notes:"
            "\n- User messages include timestamps in format [YYYY-MM-DD HH:MM:SS]. Always acknowledge when you can see these timestamps."
            "\n- Maintain conversation context - if asked a follow-up question, refer back to previous responses in the conversation."
            "\n- For workout analysis, use data from tools to provide specific, data-driven insights."
            "\n- Be encouraging and supportive about fitness progress."
            "\n- Always use tools when they can help answer questions or complete tasks."
            "\n- Be conversational and friendly, using names when you know them."
        ),
        tools=[
            tools.get_today_plan,
            tools.log_completed_set,
            tools.complete_planned_set,
            tools.new_daily_plan,
            tools.update_summary,
            tools.get_recent_history,
            tools.set_weekly_split_day,
            tools.get_weekly_split,
            tools.set_timer,
            tools.get_timer,
        ],
        model=MODEL,
    )

def run_agent(agent: Agent, user_input: str):
    """Run agent with automatic timestamp inclusion"""
    timestamped_message = f"{get_timestamp()} {user_input}"
    return Runner.run_sync(agent, timestamped_message)


