"""OpenAI Agent FunctionTool wrappers for CoachByte tools."""

from agents import function_tool
from tools import *

# Wrap each plain function
new_daily_plan = function_tool(strict_mode=False)(new_daily_plan)
get_today_plan = function_tool(strict_mode=False)(get_today_plan)
log_completed_set = function_tool(strict_mode=False)(log_completed_set)
complete_planned_set = function_tool(strict_mode=False)(complete_planned_set)
update_summary = function_tool(strict_mode=False)(update_summary)
get_recent_history = function_tool(strict_mode=False)(get_recent_history)
set_weekly_split_day = function_tool(strict_mode=False)(set_weekly_split_day)
get_weekly_split = function_tool(strict_mode=False)(get_weekly_split)
run_sql = function_tool(strict_mode=False)(run_sql)
arbitrary_update = function_tool(strict_mode=False)(arbitrary_update)
set_timer = function_tool(strict_mode=False)(set_timer)
get_timer = function_tool(strict_mode=False)(get_timer)

__all__ = [
    "new_daily_plan",
    "get_today_plan", 
    "log_completed_set",
    "complete_planned_set",
    "update_summary",
    "get_recent_history",
    "set_weekly_split_day",
    "get_weekly_split",
    "run_sql",
    "arbitrary_update",
    "set_timer",
    "get_timer",
]
