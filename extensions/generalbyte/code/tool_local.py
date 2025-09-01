"""Local GeneralByte tools (no MCP decorators).

These functions mirror the behavior and signatures of the MCP-exposed
GeneralByte tools, but can be imported and called directly.
"""

import os
from typing import Optional, Dict, Any

import requests
try:
    from dotenv import load_dotenv  # pragma: no cover
except Exception:  # pragma: no cover
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


HA_URL = os.getenv("HA_URL", "http://192.168.0.216:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
DEFAULT_NOTIFY_SERVICE = "mobile_app_jeremys_iphone"

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}


def _call_service(domain: str, service: str, data: dict) -> Dict[str, Any]:
    """Call a Home Assistant service and return the JSON response (or {})."""
    url = f"{HA_URL}/api/services/{domain}/{service}"
    response = requests.post(url, headers=HEADERS, json=data, timeout=10)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {}


def GENERAL_ACTION_send_phone_notification(message: str, title: str = "Notification", service: str | None = None) -> str:
    """Send a notification message to the configured phone via Home Assistant."""
    if not HA_TOKEN:
        return "Home Assistant token not configured"
    target_service = service or DEFAULT_NOTIFY_SERVICE
    _call_service("notify", target_service, {"title": title, "message": message})
    return "Notification sent"


def GENERAL_GET_todo_list(entity_id: str = "todo.todo", status: Optional[str] = None) -> Dict[str, Any]:
    """Return items from a Home Assistant to-do list.

    Returns a dictionary with keys: entity_id, items, total_items, available_todo_entities (or error).
    """
    if not HA_TOKEN:
        return {"error": "Home Assistant token not configured"}

    # Get all states to discover todo entities
    url_states = f"{HA_URL}/api/states"
    try:
        resp_states = requests.get(url_states, headers=HEADERS, timeout=10)
        resp_states.raise_for_status()
        all_states = resp_states.json()
    except requests.exceptions.RequestException as e:  # network / HTTP
        return {"error": f"Failed to connect to Home Assistant: {str(e)}"}
    except ValueError:
        return {"error": "Invalid response from Home Assistant"}

    todo_entities = [s.get("entity_id") for s in all_states if isinstance(s, dict) and str(s.get("entity_id", "")).startswith("todo.")]
    todo_entities = [t for t in todo_entities if t]
    if not todo_entities:
        return {"error": "No todo entities found in Home Assistant"}

    if entity_id == "todo" or entity_id not in todo_entities:
        if entity_id != "todo":
            return {
                "error": f"Todo entity '{entity_id}' not found. Available todo entities: {todo_entities}",
                "available_entities": todo_entities,
            }
        entity_id = todo_entities[0]

    # Use service API with return_response to get items
    try:
        todo_service_url = f"{HA_URL}/api/services/todo/get_items?return_response"
        resp_items = requests.post(todo_service_url, headers=HEADERS, json={"entity_id": entity_id}, timeout=10)
        resp_items.raise_for_status()
        if resp_items.status_code == 200:
            service_data = resp_items.json()
            if isinstance(service_data, dict) and "service_response" in service_data:
                entity_response = service_data["service_response"].get(entity_id, {})
                items = entity_response.get("items", [])
            else:
                items = []
        else:
            return {"error": f"Failed to get todo items: HTTP {resp_items.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to Home Assistant: {str(e)}"}

    if status:
        items = [item for item in items if item.get("status") == status]

    return {
        "entity_id": entity_id,
        "items": items,
        "total_items": len(items),
        "available_todo_entities": todo_entities,
    }


def GENERAL_ACTION_modify_todo_item(
    action: str,
    entity_id: str = "todo.todo",
    item: Optional[str] = None,
    uid: Optional[str] = None,
    rename: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    due_datetime: Optional[str] = None,
) -> str:
    """Create, update or delete a to-do list item.

    action: one of 'create', 'update', 'delete'
    """
    if not HA_TOKEN:
        return "Home Assistant token not configured"

    data: Dict[str, Any] = {"entity_id": entity_id}

    if action == "create":
        if not item:
            return "Item summary required for creation"
        data.update({"item": item})
        if description:
            data["description"] = description
        if due_date:
            data["due_date"] = due_date
        if due_datetime:
            data["due_datetime"] = due_datetime
        service = "add_item"
    elif action == "update":
        identifier = uid or item
        if not identifier:
            return "Item name or uid required for update"
        data.update({"item": identifier})
        if rename:
            data["name"] = rename
        if status:
            data["status"] = status
        if description:
            data["description"] = description
        if due_date:
            data["due_date"] = due_date
        if due_datetime:
            data["due_datetime"] = due_datetime
        service = "update_item"
    elif action == "delete":
        identifier = uid or item
        if not identifier:
            return "Item name or uid required for deletion"
        data.update({"item": identifier})
        service = "remove_item"
    else:
        return "Invalid action. Use 'create', 'update', or 'delete'."

    try:
        _call_service("todo", service, data)
        return f"Todo item {action} successful"
    except requests.exceptions.HTTPError as e:
        return f"Failed to {action} todo item: {str(e)}"


