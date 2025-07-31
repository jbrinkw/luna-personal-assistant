"""OpenAI Agent FunctionTool wrappers for CoachByte tools."""

from agents import function_tool
import coachbyte.tools as base

# Wrap each plain function
new_daily_plan = function_tool(strict_mode=False)(base.new_daily_plan)
get_today_plan = function_tool(strict_mode=False)(base.get_today_plan)
log_completed_set = function_tool(strict_mode=False)(base.log_completed_set)
complete_planned_set = function_tool(strict_mode=False)(base.complete_planned_set)
update_summary = function_tool(strict_mode=False)(base.update_summary)
get_recent_history = function_tool(strict_mode=False)(base.get_recent_history)
set_weekly_split_day = function_tool(strict_mode=False)(base.set_weekly_split_day)
get_weekly_split = function_tool(strict_mode=False)(base.get_weekly_split)
run_sql = function_tool(strict_mode=False)(base.run_sql)
arbitrary_update = function_tool(strict_mode=False)(base.arbitrary_update)
set_timer = function_tool(strict_mode=False)(base.set_timer)
get_timer = function_tool(strict_mode=False)(base.get_timer)

__all__ = base.__all__
