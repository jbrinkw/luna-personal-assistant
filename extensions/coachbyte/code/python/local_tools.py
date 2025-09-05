"""Local CoachByte tools (no MCP decorators).

Re-exports COACH_* functions defined in the aggregated MCP server for direct import.
"""

from __future__ import annotations

try:
    from .coachbyte_mcp_server import (
        COACH_UPDATE_new_daily_plan,
        COACH_GET_today_plan,
        COACH_UPDATE_log_completed_set,
        COACH_UPDATE_complete_planned_set,
        COACH_UPDATE_summary,
        COACH_GET_recent_history,
        COACH_UPDATE_set_weekly_split_day,
        COACH_GET_weekly_split,
        COACH_ACTION_rewrite_todays_plan,
        COACH_ACTION_set_timer,
        COACH_GET_timer,
    )
except (ModuleNotFoundError, ImportError):  # pragma: no cover
    import sys as _sys
    import os as _os
    _sys.path.insert(0, _os.path.abspath(_os.path.dirname(__file__)))
    from coachbyte_mcp_server import (  # type: ignore
        COACH_UPDATE_new_daily_plan,
        COACH_GET_today_plan,
        COACH_UPDATE_log_completed_set,
        COACH_UPDATE_complete_planned_set,
        COACH_UPDATE_summary,
        COACH_GET_recent_history,
        COACH_UPDATE_set_weekly_split_day,
        COACH_GET_weekly_split,
        COACH_ACTION_rewrite_todays_plan,
        COACH_ACTION_set_timer,
        COACH_GET_timer,
    )

__all__ = [
    "COACH_UPDATE_new_daily_plan",
    "COACH_GET_today_plan",
    "COACH_UPDATE_log_completed_set",
    "COACH_UPDATE_complete_planned_set",
    "COACH_UPDATE_summary",
    "COACH_GET_recent_history",
    "COACH_UPDATE_set_weekly_split_day",
    "COACH_GET_weekly_split",
    "COACH_ACTION_rewrite_todays_plan",
    "COACH_ACTION_set_timer",
    "COACH_GET_timer",
]



