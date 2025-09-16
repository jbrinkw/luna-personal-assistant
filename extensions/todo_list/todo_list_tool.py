"""Todo List extension — manage tasks via Todoist REST API.

This extension wraps Todoist task operations (list, create, update, complete)
and exposes them as callable tools for the domain agent.
"""

from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field

try:  # pragma: no cover
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


# --- Configuration ---
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
TODOIST_REST_BASE = "https://api.todoist.com/rest/v2"
TASKS_ENDPOINT = f"{TODOIST_REST_BASE}/tasks"
PROJECTS_ENDPOINT = f"{TODOIST_REST_BASE}/projects"
SECTIONS_ENDPOINT = f"{TODOIST_REST_BASE}/sections"


# --- Minimal models (Pydantic optional in this module) ---
def _require_token() -> Optional[str]:
    if not TODOIST_API_TOKEN:
        return "Error: TODOIST_API_TOKEN environment variable not set!"
    return None


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {TODOIST_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(method: str, url: str, data: Optional[Dict[str, Any]] = None) -> Tuple[int, Optional[Any]]:
    import urllib.request
    import urllib.error

    body: Optional[bytes] = None
    headers = _headers()
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            payload = resp.read().decode("utf-8") if resp.length is None or resp.length > 0 else ""
            ctype = resp.headers.get("Content-Type", "")
            if payload and "application/json" in ctype:
                try:
                    return status, json.loads(payload)
                except Exception:
                    return status, payload
            return status, payload if payload else None
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
        except Exception:
            raw = "<no details>"
        return e.code, {"error": raw}
    except urllib.error.URLError as e:
        return 0, {"error": str(e)}


def _get(url: str) -> Any:
    status, data = _request("GET", url)
    if status != 200:
        raise RuntimeError(f"Unexpected status {status} for GET {url}: {data}")
    return data


def _post(url: str, data: Optional[Dict[str, Any]] = None, expected: Tuple[int, ...] = (200, 201, 204)) -> Optional[Any]:
    status, payload = _request("POST", url, data)
    if status not in expected:
        raise RuntimeError(f"Unexpected status {status} for POST {url}: {payload}")
    return payload


def _urlencode(params: Dict[str, Any]) -> str:
    from urllib.parse import urlencode
    return urlencode(params)


def _fetch_projects() -> List[Dict[str, Any]]:
    data = _get(PROJECTS_ENDPOINT)
    return data if isinstance(data, list) else []


def _fetch_sections(project_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if project_id is not None:
        from urllib.parse import urlencode
        url = f"{SECTIONS_ENDPOINT}?{urlencode({'project_id': int(project_id)})}"
        data = _get(url)
        return data if isinstance(data, list) else []
    data = _get(SECTIONS_ENDPOINT)
    return data if isinstance(data, list) else []


def _fetch_tasks(filter_query: Optional[str] = None) -> List[Dict[str, Any]]:
    url = TASKS_ENDPOINT
    if filter_query:
        url = f"{url}?{_urlencode({'filter': filter_query})}"
    data = _get(url)
    return data if isinstance(data, list) else []


def _enrich_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    projects = {int(p["id"]): p for p in _fetch_projects()}
    sections = {int(s["id"]): s for s in _fetch_sections()}
    enriched: List[Dict[str, Any]] = []
    for t in tasks:
        pid = int(t.get("project_id")) if t.get("project_id") is not None else None
        sid = int(t.get("section_id")) if t.get("section_id") is not None else None
        enriched.append({
            **t,
            "project": {"id": pid, "name": projects.get(pid, {}).get("name") if pid is not None else None},
            "section": {"id": sid, "name": sections.get(sid, {}).get("name") if sid is not None else None},
        })
    return enriched


# --- Pydantic models for structured outputs ---

class OperationResult(BaseModel):
    success: bool
    message: str


class TodoProject(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class TodoSection(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None


class TodoTask(BaseModel):
    id: Optional[int] = None
    content: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    project_id: Optional[int] = None
    section_id: Optional[int] = None
    due: Dict[str, Any] = Field(default_factory=dict)
    url: Optional[str] = None
    project: Optional[TodoProject] = None
    section: Optional[TodoSection] = None


class ListTasksResponse(BaseModel):
    success: bool
    count: int
    tasks: List[TodoTask] = Field(default_factory=list)
    message: Optional[str] = None


class ListProjectsResponse(BaseModel):
    success: bool
    count: int
    projects: List[TodoProject] = Field(default_factory=list)
    message: Optional[str] = None


class ListSectionsResponse(BaseModel):
    success: bool
    count: int
    sections: List[TodoSection] = Field(default_factory=list)
    message: Optional[str] = None


class TaskEnvelope(BaseModel):
    success: bool
    task: Optional[TodoTask] = None
    updated: Optional[bool] = None
    completed: Optional[bool] = None
    task_id: Optional[int] = None
    message: Optional[str] = None


def _to_task_model(item: Dict[str, Any]) -> TodoTask:
    return TodoTask(
        id=item.get("id"),
        content=item.get("content"),
        description=item.get("description"),
        priority=item.get("priority"),
        project_id=item.get("project_id"),
        section_id=item.get("section_id"),
        due=item.get("due") or {},
        url=item.get("url"),
        project=TodoProject(**item.get("project", {})) if isinstance(item.get("project"), dict) else None,
        section=TodoSection(**item.get("section", {})) if isinstance(item.get("section"), dict) else None,
    )


# Ensure forward refs are resolved under postponed annotations
OperationResult.model_rebuild()
TodoProject.model_rebuild()
TodoSection.model_rebuild()
TodoTask.model_rebuild()
ListTasksResponse.model_rebuild()
ListProjectsResponse.model_rebuild()
ListSectionsResponse.model_rebuild()
TaskEnvelope.model_rebuild()


# --- Extension metadata ---
NAME = "Todo List"

SYSTEM_PROMPT = """
Manage the user's to-do list using Todoist.
Use precise, explicit fields when creating or updating tasks; prefer adding context in descriptions.
You can list tasks with optional filters, create new tasks, update existing tasks, and complete tasks.
"""


# --- Tools ---
def TODOLIST_GET_list_projects() -> ListProjectsResponse:
    """List Todoist projects.
    Example Prompt: List my Todoist projects.
    Example Response: {"success": true, "count": 2, "projects": [{"id": 1, "name": "Inbox"}]}
    Example Args: {}
    Returns a JSON object with all projects.
    """
    err = _require_token()
    if err:
        return ListProjectsResponse(success=False, count=0, projects=[], message=err)
    try:
        items = _fetch_projects()
        models = [TodoProject(id=int(p.get("id")) if p.get("id") is not None else None, name=p.get("name")) for p in items]
        return ListProjectsResponse(success=True, count=len(models), projects=models)
    except Exception as e:
        return ListProjectsResponse(success=False, count=0, projects=[], message=str(e))


def TODOLIST_GET_list_sections(project_id: Optional[int] = None) -> ListSectionsResponse:
    """List Todoist sections (optionally filtered by project).
    Example Prompt: List sections in project 123.
    Example Response: {"success": true, "count": 2, "sections": [{"id": 10, "name": "Today"}]}
    Example Args: {"project_id": 123}
    Returns a JSON object with sections; pass project_id to filter.
    """
    err = _require_token()
    if err:
        return ListSectionsResponse(success=False, count=0, sections=[], message=err)
    try:
        items = _fetch_sections(project_id=project_id)
        models = [TodoSection(id=int(s.get("id")) if s.get("id") is not None else None, name=s.get("name")) for s in items]
        return ListSectionsResponse(success=True, count=len(models), sections=models)
    except Exception as e:
        return ListSectionsResponse(success=False, count=0, sections=[], message=str(e))


def TODOLIST_GET_task_by_id(task_id: int) -> TaskEnvelope:
    """Get a single Todoist task by ID, enriched with project/section names.
    Example Prompt: Show task 123 details.
    Example Response: {"success": true, "task": {"id": 123, "content": "Buy groceries", "project": {"id": 1, "name": "Personal"}, "section": {"id": 2, "name": "Shopping"}}}
    Example Args: {"task_id": int}
    """
    err = _require_token()
    if err:
        return TaskEnvelope(success=False, message=err)
    try:
        raw = _get(f"{TASKS_ENDPOINT}/{int(task_id)}")
        if not isinstance(raw, dict):
            return TaskEnvelope(success=False, message="Task not found or unexpected response", task_id=int(task_id))
        enriched = _enrich_tasks([raw])
        model = _to_task_model(enriched[0]) if enriched else _to_task_model(raw)
        return TaskEnvelope(success=True, task=model)
    except Exception as e:
        return TaskEnvelope(success=False, message=str(e), task_id=int(task_id))


def TODOLIST_GET_list_tasks(filter: Optional[str] = None) -> ListTasksResponse:
    """List active Todoist tasks with project and section names.
    Example Prompt: Show my tasks for today.
    Example Response: {"success": true, "count": 2, "tasks": [{"id": 123, "content": "string", "project_id": 1, "section_id": 2, "due": {}}]}
    Example Args: {"filter": "string[Todoist filter query like 'today | overdue']"}
    Returns a JSON object with tasks, enriched with project/section names. Accepts Todoist filter syntax, e.g., "today | overdue".
    """
    err = _require_token()
    if err:
        return ListTasksResponse(success=False, count=0, tasks=[], message=err)
    tasks = _fetch_tasks(filter_query=filter)
    enriched = _enrich_tasks(tasks)
    models = [_to_task_model(t) for t in enriched]
    return ListTasksResponse(success=True, count=len(models), tasks=models)


def TODOLIST_ACTION_create_task(
    content: str,
    project_id: int,
    section_id: Optional[int] = None,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    due_string: Optional[str] = None,
    due_date: Optional[str] = None,
    due_datetime: Optional[str] = None,
) -> TaskEnvelope:
    """Create a Todoist task in a project (optional section).
    Example Prompt: Create a task: "Add 'Buy milk' to Inbox for today".
    Example Response: {"success": true, "task": {"id": 123, "content": "string", "project_id": 1}}
    Example Args: {"content": "string", "project_id": int, "section_id": int, "description": "string", "priority": int[1-4], "due_string": "string", "due_date": "YYYY-MM-DD", "due_datetime": "ISO8601"}
    Required: content, project_id. Optional: section_id, description, priority (1-4), due_string, due_date, due_datetime.
    """
    err = _require_token()
    if err:
        return TaskEnvelope(success=False, message=err)
    payload: Dict[str, Any] = {"content": content, "project_id": int(project_id)}
    if section_id is not None:
        payload["section_id"] = int(section_id)
    if description is not None:
        payload["description"] = description
    if priority is not None:
        payload["priority"] = int(priority)
    if due_string is not None:
        payload["due_string"] = due_string
    if due_date is not None:
        payload["due_date"] = due_date
    if due_datetime is not None:
        payload["due_datetime"] = due_datetime
    created = _post(TASKS_ENDPOINT, data=payload, expected=(200, 201))
    if isinstance(created, dict):
        return TaskEnvelope(success=True, task=_to_task_model(created))
    return TaskEnvelope(success=True, message="Created")


def TODOLIST_UPDATE_update_task(
    task_id: int,
    content: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    due_string: Optional[str] = None,
    due_date: Optional[str] = None,
    due_datetime: Optional[str] = None,
    project_id: Optional[int] = None,
    section_id: Optional[int] = None,
) -> TaskEnvelope:
    """Update a Todoist task by ID; only provided fields change.
    Example Prompt: Update task 123 to due tomorrow at 9am.
    Example Response: {"success": true, "updated": true, "task_id": 123}
    Example Args: {"task_id": int, "content": "string", "description": "string", "priority": int[1-4], "due_string": "string", "due_date": "YYYY-MM-DD", "due_datetime": "ISO8601", "project_id": int, "section_id": int}
    Can also move tasks across projects/sections.
    """
    err = _require_token()
    if err:
        return TaskEnvelope(success=False, message=err)
    payload: Dict[str, Any] = {}
    if content is not None:
        payload["content"] = content
    if description is not None:
        payload["description"] = description
    if priority is not None:
        payload["priority"] = int(priority)
    if due_string is not None:
        payload["due_string"] = due_string
    if due_date is not None:
        payload["due_date"] = due_date
    if due_datetime is not None:
        payload["due_datetime"] = due_datetime
    if project_id is not None:
        payload["project_id"] = int(project_id)
    if section_id is not None:
        payload["section_id"] = int(section_id)
    if not payload:
        return TaskEnvelope(success=False, message="No fields provided to update")
    url = f"{TASKS_ENDPOINT}/{int(task_id)}"
    updated = _post(url, data=payload, expected=(200, 204))
    if isinstance(updated, dict):
        return TaskEnvelope(success=True, task=_to_task_model(updated))
    return TaskEnvelope(success=True, updated=True, task_id=int(task_id))


def TODOLIST_ACTION_complete_task(task_id: int) -> TaskEnvelope:
    """Complete (close) a Todoist task by ID.
    Example Prompt: Complete task 123.
    Example Response: {"success": true, "completed": true, "task_id": 123}
    Example Args: {"task_id": int}
    Returns success indicator and task_id.
    """
    err = _require_token()
    if err:
        return TaskEnvelope(success=False, message=err)
    url = f"{TASKS_ENDPOINT}/{int(task_id)}/close"
    _post(url, data=None, expected=(204,))
    return TaskEnvelope(success=True, completed=True, task_id=int(task_id))


TOOLS = [
    TODOLIST_GET_list_projects,
    TODOLIST_GET_list_sections,
    TODOLIST_GET_task_by_id,
    TODOLIST_GET_list_tasks,
    TODOLIST_ACTION_create_task,
    TODOLIST_UPDATE_update_task,
    TODOLIST_ACTION_complete_task,
]


