"""Auto-generated fake tool module. Do not edit by hand.

This module mirrors function names, signatures, and docstrings from the
original tool, but contains no operational code. All functions return None.
"""
from __future__ import annotations

NAME = 'Todo List'
SYSTEM_PROMPT = "\nManage the user's to-do list using Todoist.\nUse precise, explicit fields when creating or updating tasks; prefer adding context in descriptions.\nYou can list tasks with optional filters, create new tasks, update existing tasks, and complete tasks.\n"

def TODOLIST_GET_list_tasks(filter: Optional[str] = None) -> ListTasksResponse:
    """List active Todoist tasks with project and section names.
    Show my tasks for today.
    Returns a JSON object with tasks, enriched with project/section names. Accepts Todoist filter syntax, e.g., "today | overdue".
    """
    return None

def TODOLIST_ACTION_create_task(content: str, project_id: int, section_id: Optional[int] = None, description: Optional[str] = None, priority: Optional[int] = None, due_string: Optional[str] = None, due_date: Optional[str] = None, due_datetime: Optional[str] = None) -> TaskEnvelope:
    """Create a Todoist task in a project (optional section).
    Create a task: "Add 'Buy milk' to Inbox for today".
    Required: content, project_id. Optional: section_id, description, priority (1-4), due_string, due_date, due_datetime.
    """
    return None

def TODOLIST_UPDATE_update_task(task_id: int, content: Optional[str] = None, description: Optional[str] = None, priority: Optional[int] = None, due_string: Optional[str] = None, due_date: Optional[str] = None, due_datetime: Optional[str] = None, project_id: Optional[int] = None, section_id: Optional[int] = None) -> TaskEnvelope:
    """Update a Todoist task by ID; only provided fields change.
    Update task 123 to due tomorrow at 9am.
    Can also move tasks across projects/sections.
    """
    return None

def TODOLIST_ACTION_complete_task(task_id: int) -> TaskEnvelope:
    """Complete (close) a Todoist task by ID.
    Complete task 123.
    Returns success indicator and task_id.
    """
    return None

TOOLS = [TODOLIST_GET_list_tasks, TODOLIST_ACTION_create_task, TODOLIST_UPDATE_update_task, TODOLIST_ACTION_complete_task]

__all__ = ['NAME', 'SYSTEM_PROMPT', 'TOOLS', 'TODOLIST_GET_list_tasks', 'TODOLIST_ACTION_create_task', 'TODOLIST_UPDATE_update_task', 'TODOLIST_ACTION_complete_task']
