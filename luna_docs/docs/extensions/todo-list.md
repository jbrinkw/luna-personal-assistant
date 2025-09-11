# Todo List — User Guide

## Purpose
Manage tasks via the Todoist REST API: list, create, update, and complete tasks.

## Prerequisites
- Environment: `TODOIST_API_TOKEN` must be set.

## Tools

### `TODOLIST_GET_list_projects`
- Summary: List Todoist projects.
- Example Prompt: List my Todoist projects.
- Example Args: {}
- Returns: {"success": bool, "count": number, "projects": [{"id", "name"}]}.

### `TODOLIST_GET_list_sections`
- Summary: List Todoist sections (optionally filtered by project).
- Example Prompt: List sections in project 123.
- Example Args: {"project_id": 123}
- Returns: {"success": bool, "count": number, "sections": [{"id", "name"}]}.

### `TODOLIST_GET_task_by_id`
- Summary: Get a single Todoist task by ID, enriched with project/section names.
- Example Prompt: Show task 123 details.
- Example Args: {"task_id": 123}
- Returns: {"success": bool, "task": {"id", "content", ...}}.

### `TODOLIST_GET_list_tasks`
- Summary: List active Todoist tasks with project and section names.
- Example Prompt: Show my tasks for today.
- Example Args: {"filter": "string[Todoist filter query like 'today | overdue']"}
- Returns: {"success": bool, "count": number, "tasks": [...] }.

### `TODOLIST_ACTION_create_task`
- Summary: Create a Todoist task in a project (optional section).
- Example Prompt: Create a task: "Add 'Buy milk' to Inbox for today".
- Example Args: {"content": "string", "project_id": int, "section_id": int, "description": "string", "priority": int, "due_string": "string", "due_date": "YYYY-MM-DD", "due_datetime": "ISO8601"}
- Returns: {"success": bool, "task": {"id", "content", ...}} or {"success": true, "message": "Created"}.

### `TODOLIST_UPDATE_update_task`
- Summary: Update a Todoist task by ID; only provided fields change.
- Example Prompt: Update task 123 to due tomorrow at 9am.
- Example Args: {"task_id": int, "content": "string", "description": "string", "priority": int, "due_string": "string", "due_date": "YYYY-MM-DD", "due_datetime": "ISO8601", "project_id": int, "section_id": int}
- Returns: {"success": bool, "updated": bool, "task_id": int} or full task.

### `TODOLIST_ACTION_complete_task`
- Summary: Complete (close) a Todoist task by ID.
- Example Prompt: Complete task 123.
- Example Args: {"task_id": int}
- Returns: {"success": bool, "completed": bool, "task_id": int}.
