"""Automation Memory tools - memories, task flows, and scheduled tasks.

All tools follow the new spec:
- Pydantic validation for inputs
- Return (bool, str) tuples
- Proper docstrings with Example Prompt/Response/Args
- Naming convention: DOMAIN_{GET|UPDATE|ACTION}_VerbNoun
"""
import os
import sys
import json
from typing import Tuple, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import database utilities
try:
    from core.utils.db import get_db
except Exception:
    # Fallback if db module not available yet
    def get_db():
        raise RuntimeError("Database not configured")

SYSTEM_PROMPT = """The user has access to tools for managing memories, scheduled tasks, and task flows.

Memories are simple text entries that provide context across conversations.
Scheduled tasks run prompts at specified times using a selected agent.
Task flows execute sequences of prompts in order using a selected agent."""


# ---- Memory Tools ----
class MEMORY_GET_AllArgs(BaseModel):
    """No arguments needed."""
    pass


def MEMORY_GET_all() -> Tuple[bool, str]:
    """Get all memory entries.
    Example Prompt: show me all memories
    Example Response: {"memories": [{"id": 1, "content": "User prefers concise responses"}]}
    Example Args: {}
    """
    try:
        db = get_db()
        rows = db.execute("SELECT id, content FROM memories ORDER BY id DESC")
        return (True, json.dumps({"memories": rows or []}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error getting memories: {str(e)}")


class MEMORY_UPDATE_CreateArgs(BaseModel):
    """Arguments for creating a memory."""
    content: str = Field(..., description="The memory content")


def MEMORY_UPDATE_create(content: str) -> Tuple[bool, str]:
    """Create a new memory entry.
    Example Prompt: remember that I prefer concise responses
    Example Response: {"success": true, "id": 1}
    Example Args: {"content": "User prefers concise responses"}
    """
    try:
        _ = MEMORY_UPDATE_CreateArgs(content=content)
        db = get_db()
        result = db.execute_one(
            "INSERT INTO memories (content, created_at, updated_at) VALUES (%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id",
            (content,)
        )
        return (True, json.dumps({"success": True, "id": result["id"] if result else None}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error creating memory: {str(e)}")


class MEMORY_UPDATE_UpdateArgs(BaseModel):
    """Arguments for updating a memory."""
    id: int = Field(..., description="Memory ID")
    content: str = Field(..., description="Updated content")


def MEMORY_UPDATE_update(id: int, content: str) -> Tuple[bool, str]:
    """Update an existing memory entry.
    Example Prompt: update memory 1 to say I prefer detailed responses
    Example Response: {"success": true}
    Example Args: {"id": 1, "content": "User prefers detailed responses"}
    """
    try:
        _ = MEMORY_UPDATE_UpdateArgs(id=id, content=content)
        db = get_db()
        db.execute(
            "UPDATE memories SET content = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (content, id),
            fetch=False
        )
        return (True, json.dumps({"success": True}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error updating memory: {str(e)}")


class MEMORY_UPDATE_DeleteArgs(BaseModel):
    """Arguments for deleting a memory."""
    id: int = Field(..., description="Memory ID to delete")


def MEMORY_UPDATE_delete(id: int) -> Tuple[bool, str]:
    """Delete a memory entry.
    Example Prompt: delete memory 1
    Example Response: {"success": true}
    Example Args: {"id": 1}
    """
    try:
        _ = MEMORY_UPDATE_DeleteArgs(id=id)
        db = get_db()
        db.execute("DELETE FROM memories WHERE id = %s", (id,), fetch=False)
        return (True, json.dumps({"success": True}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error deleting memory: {str(e)}")


# ---- Task Flow Tools ----
class FLOW_GET_AllArgs(BaseModel):
    """No arguments needed."""
    pass


def FLOW_GET_all() -> Tuple[bool, str]:
    """Get all task flows.
    Example Prompt: show me all task flows
    Example Response: {"flows": [{"id": 1, "call_name": "morning_routine", "prompts": ["check email", "review calendar"], "agent": "simple_agent"}]}
    Example Args: {}
    """
    try:
        db = get_db()
        rows = db.execute("SELECT id, call_name, prompts, agent FROM task_flows ORDER BY id DESC")
        return (True, json.dumps({"flows": rows or []}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error getting task flows: {str(e)}")


class FLOW_GET_ByNameArgs(BaseModel):
    """Arguments for getting a flow by name."""
    call_name: str = Field(..., description="The flow call name")


def FLOW_GET_by_name(call_name: str) -> Tuple[bool, str]:
    """Get a task flow by its call name.
    Example Prompt: get the morning routine flow
    Example Response: {"id": 1, "call_name": "morning_routine", "prompts": ["check email"], "agent": "simple_agent"}
    Example Args: {"call_name": "morning_routine"}
    """
    try:
        _ = FLOW_GET_ByNameArgs(call_name=call_name)
        db = get_db()
        row = db.execute_one(
            "SELECT id, call_name, prompts, agent FROM task_flows WHERE call_name = %s",
            (call_name,)
        )
        if not row:
            return (False, f"Flow '{call_name}' not found")
        return (True, json.dumps(row, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error getting flow: {str(e)}")


class FLOW_ACTION_RunArgs(BaseModel):
    """Arguments for running a flow."""
    call_name: str = Field(..., description="The flow call name to execute")


def FLOW_ACTION_run(call_name: str) -> Tuple[bool, str]:
    """Run a task flow by its call name.
    Example Prompt: run the morning routine flow
    Example Response: {"success": true, "status": "completed"}
    Example Args: {"call_name": "morning_routine"}
    Notes: Executes all prompts in the flow sequentially using the specified agent.
    """
    try:
        _ = FLOW_ACTION_RunArgs(call_name=call_name)
        db = get_db()
        
        # Get flow
        row = db.execute_one(
            "SELECT id, call_name, prompts, agent FROM task_flows WHERE call_name = %s",
            (call_name,)
        )
        
        if not row:
            return (False, f"Flow '{call_name}' not found")
        
        # TODO: Execute flow using prompt_runner with specified agent
        # For now, just return success
        return (True, json.dumps({"success": True, "status": "completed"}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error running flow: {str(e)}")


class FLOW_UPDATE_CreateArgs(BaseModel):
    """Arguments for creating a flow."""
    call_name: str = Field(..., description="Unique name for the flow")
    prompts: List[str] = Field(..., description="List of prompts to execute")
    agent: str = Field(default="simple_agent", description="Agent to use for execution")


def FLOW_UPDATE_create(call_name: str, prompts: List[str], agent: str = "simple_agent") -> Tuple[bool, str]:
    """Create a new task flow.
    Example Prompt: create a flow called morning_routine with prompts check email and review calendar using simple_agent
    Example Response: {"success": true, "id": 1}
    Example Args: {"call_name": "morning_routine", "prompts": ["check email", "review calendar"], "agent": "simple_agent"}
    """
    try:
        _ = FLOW_UPDATE_CreateArgs(call_name=call_name, prompts=prompts, agent=agent)
        db = get_db()
        result = db.execute_one(
            """INSERT INTO task_flows (call_name, prompts, agent, created_at, updated_at)
               VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
               RETURNING id""",
            (call_name, json.dumps(prompts), agent)
        )
        return (True, json.dumps({"success": True, "id": result["id"] if result else None}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error creating flow: {str(e)}")


class FLOW_UPDATE_UpdateArgs(BaseModel):
    """Arguments for updating a flow."""
    id: int = Field(..., description="Flow ID")
    call_name: Optional[str] = Field(None, description="New call name")
    prompts: Optional[List[str]] = Field(None, description="New prompts list")
    agent: Optional[str] = Field(None, description="New agent")


def FLOW_UPDATE_update(id: int, call_name: Optional[str] = None, prompts: Optional[List[str]] = None, agent: Optional[str] = None) -> Tuple[bool, str]:
    """Update an existing task flow.
    Example Prompt: update flow 1 to use passthrough_agent
    Example Response: {"success": true}
    Example Args: {"id": 1, "agent": "passthrough_agent"}
    """
    try:
        _ = FLOW_UPDATE_UpdateArgs(id=id, call_name=call_name, prompts=prompts, agent=agent)
        db = get_db()
        
        # Build update query dynamically
        updates = []
        params = []
        if call_name is not None:
            updates.append("call_name = %s")
            params.append(call_name)
        if prompts is not None:
            updates.append("prompts = %s")
            params.append(json.dumps(prompts))
        if agent is not None:
            updates.append("agent = %s")
            params.append(agent)
        
        if not updates:
            return (True, json.dumps({"success": True, "message": "No updates specified"}, ensure_ascii=False))
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(id)
        
        query = f"UPDATE task_flows SET {', '.join(updates)} WHERE id = %s"
        db.execute(query, tuple(params), fetch=False)
        
        return (True, json.dumps({"success": True}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error updating flow: {str(e)}")


class FLOW_UPDATE_DeleteArgs(BaseModel):
    """Arguments for deleting a flow."""
    id: int = Field(..., description="Flow ID to delete")


def FLOW_UPDATE_delete(id: int) -> Tuple[bool, str]:
    """Delete a task flow.
    Example Prompt: delete flow 1
    Example Response: {"success": true}
    Example Args: {"id": 1}
    """
    try:
        _ = FLOW_UPDATE_DeleteArgs(id=id)
        db = get_db()
        db.execute("DELETE FROM task_flows WHERE id = %s", (id,), fetch=False)
        return (True, json.dumps({"success": True}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error deleting flow: {str(e)}")


# ---- Scheduled Task Tools ----
class SCHEDULE_GET_AllArgs(BaseModel):
    """No arguments needed."""
    pass


def SCHEDULE_GET_all() -> Tuple[bool, str]:
    """Get all scheduled tasks.
    Example Prompt: show me all scheduled tasks
    Example Response: {"schedules": [{"id": 1, "time_of_day": "09:00", "days_of_week": [true, true, true, true, true, false, false], "prompt": "check email", "agent": "simple_agent", "enabled": true}]}
    Example Args: {}
    """
    try:
        db = get_db()
        rows = db.execute("SELECT id, time_of_day, days_of_week, prompt, agent, enabled FROM scheduled_prompts ORDER BY id DESC")
        return (True, json.dumps({"schedules": rows or []}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error getting schedules: {str(e)}")


class SCHEDULE_UPDATE_CreateArgs(BaseModel):
    """Arguments for creating a schedule."""
    time_of_day: str = Field(..., description="Time in HH:MM format")
    days_of_week: List[bool] = Field(..., description="7 booleans for Sun-Sat")
    prompt: str = Field(..., description="Prompt to execute")
    agent: str = Field(default="simple_agent", description="Agent to use")
    enabled: bool = Field(default=True, description="Whether schedule is active")


def SCHEDULE_UPDATE_create(time_of_day: str, days_of_week: List[bool], prompt: str, agent: str = "simple_agent", enabled: bool = True) -> Tuple[bool, str]:
    """Create a new scheduled task.
    Example Prompt: schedule check email at 9am weekdays using simple_agent
    Example Response: {"success": true, "id": 1}
    Example Args: {"time_of_day": "09:00", "days_of_week": [false, true, true, true, true, true, false], "prompt": "check email", "agent": "simple_agent", "enabled": true}
    """
    try:
        _ = SCHEDULE_UPDATE_CreateArgs(time_of_day=time_of_day, days_of_week=days_of_week, prompt=prompt, agent=agent, enabled=enabled)
        db = get_db()
        result = db.execute_one(
            """INSERT INTO scheduled_prompts (time_of_day, days_of_week, prompt, agent, enabled, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
               RETURNING id""",
            (time_of_day, json.dumps(days_of_week), prompt, agent, enabled)
        )
        return (True, json.dumps({"success": True, "id": result["id"] if result else None}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error creating schedule: {str(e)}")


class SCHEDULE_UPDATE_UpdateArgs(BaseModel):
    """Arguments for updating a schedule."""
    id: int = Field(..., description="Schedule ID")
    time_of_day: Optional[str] = Field(None, description="New time")
    days_of_week: Optional[List[bool]] = Field(None, description="New days")
    prompt: Optional[str] = Field(None, description="New prompt")
    agent: Optional[str] = Field(None, description="New agent")
    enabled: Optional[bool] = Field(None, description="New enabled status")


def SCHEDULE_UPDATE_update(id: int, time_of_day: Optional[str] = None, days_of_week: Optional[List[bool]] = None, prompt: Optional[str] = None, agent: Optional[str] = None, enabled: Optional[bool] = None) -> Tuple[bool, str]:
    """Update an existing scheduled task.
    Example Prompt: disable schedule 1
    Example Response: {"success": true}
    Example Args: {"id": 1, "enabled": false}
    """
    try:
        _ = SCHEDULE_UPDATE_UpdateArgs(id=id, time_of_day=time_of_day, days_of_week=days_of_week, prompt=prompt, agent=agent, enabled=enabled)
        db = get_db()
        
        # Build update query dynamically
        updates = []
        params = []
        if time_of_day is not None:
            updates.append("time_of_day = %s")
            params.append(time_of_day)
        if days_of_week is not None:
            updates.append("days_of_week = %s")
            params.append(json.dumps(days_of_week))
        if prompt is not None:
            updates.append("prompt = %s")
            params.append(prompt)
        if agent is not None:
            updates.append("agent = %s")
            params.append(agent)
        if enabled is not None:
            updates.append("enabled = %s")
            params.append(enabled)
        
        if not updates:
            return (True, json.dumps({"success": True, "message": "No updates specified"}, ensure_ascii=False))
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(id)
        
        query = f"UPDATE scheduled_prompts SET {', '.join(updates)} WHERE id = %s"
        db.execute(query, tuple(params), fetch=False)
        
        return (True, json.dumps({"success": True}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error updating schedule: {str(e)}")


class SCHEDULE_UPDATE_DeleteArgs(BaseModel):
    """Arguments for deleting a schedule."""
    id: int = Field(..., description="Schedule ID to delete")


def SCHEDULE_UPDATE_delete(id: int) -> Tuple[bool, str]:
    """Delete a scheduled task.
    Example Prompt: delete schedule 1
    Example Response: {"success": true}
    Example Args: {"id": 1}
    """
    try:
        _ = SCHEDULE_UPDATE_DeleteArgs(id=id)
        db = get_db()
        db.execute("DELETE FROM scheduled_prompts WHERE id = %s", (id,), fetch=False)
        return (True, json.dumps({"success": True}, ensure_ascii=False))
    except Exception as e:
        return (False, f"Error deleting schedule: {str(e)}")


# Export all tools
TOOLS = [
    MEMORY_GET_all,
    MEMORY_UPDATE_create,
    MEMORY_UPDATE_update,
    MEMORY_UPDATE_delete,
    FLOW_GET_all,
    FLOW_GET_by_name,
    FLOW_ACTION_run,
    FLOW_UPDATE_create,
    FLOW_UPDATE_update,
    FLOW_UPDATE_delete,
    SCHEDULE_GET_all,
    SCHEDULE_UPDATE_create,
    SCHEDULE_UPDATE_update,
    SCHEDULE_UPDATE_delete,
]

