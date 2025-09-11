"""Auto-generated fake tools for tests. DO NOT EDIT BY HAND."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


NAME = "Todo List"

SYSTEM_PROMPT = """
Manage the user's to-do list using Todoist.
Use precise, explicit fields when creating or updating tasks; prefer adding context in descriptions.
You can list tasks with optional filters, create new tasks, update existing tasks, and complete tasks.
"""



def TODOLIST_GET_list_tasks(filter: 'Optional[str]' = None):
	"""List active Todoist tasks with project and section names.
Show my tasks for today.
Example Response: {"success": true, "count": 2, "tasks": [{"id": 123, "content": "string", "project_id": 1, "section_id": 2, "due": {}}]}
Returns a JSON object with tasks, enriched with project/section names. Accepts Todoist filter syntax, e.g., "today | overdue".
	"""
	return '{"success": true, "count": 2, "tasks": [{"id": 123, "content": "string", "project_id": 1, "section_id": 2, "due": {}}]}'


def TODOLIST_ACTION_create_task(content: 'str', project_id: 'int', section_id: 'Optional[int]' = None, description: 'Optional[str]' = None, priority: 'Optional[int]' = None, due_string: 'Optional[str]' = None, due_date: 'Optional[str]' = None, due_datetime: 'Optional[str]' = None):
	"""Create a Todoist task in a project (optional section).
Create a task: "Add 'Buy milk' to Inbox for today".
Example Response: {"success": true, "task": {"id": 123, "content": "string", "project_id": 1}}
Required: content, project_id. Optional: section_id, description, priority (1-4), due_string, due_date, due_datetime.
	"""
	return '{"success": true, "task": {"id": 123, "content": "string", "project_id": 1}}'


def TODOLIST_UPDATE_update_task(task_id: 'int', content: 'Optional[str]' = None, description: 'Optional[str]' = None, priority: 'Optional[int]' = None, due_string: 'Optional[str]' = None, due_date: 'Optional[str]' = None, due_datetime: 'Optional[str]' = None, project_id: 'Optional[int]' = None, section_id: 'Optional[int]' = None):
	"""Update a Todoist task by ID; only provided fields change.
Update task 123 to due tomorrow at 9am.
Example Response: {"success": true, "updated": true, "task_id": 123}
Can also move tasks across projects/sections.
	"""
	return '{"success": true, "updated": true, "task_id": 123}'


def TODOLIST_ACTION_complete_task(task_id: 'int'):
	"""Complete (close) a Todoist task by ID.
Complete task 123.
Example Response: {"success": true, "completed": true, "task_id": 123}
Returns success indicator and task_id.
	"""
	return '{"success": true, "completed": true, "task_id": 123}'


TOOLS = [
	TODOLIST_GET_list_tasks,
	TODOLIST_ACTION_create_task,
	TODOLIST_UPDATE_update_task,
	TODOLIST_ACTION_complete_task
]
