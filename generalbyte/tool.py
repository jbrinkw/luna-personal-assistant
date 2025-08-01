"""Tools for notifications and to-do lists via Home Assistant."""

import os
from typing import Optional

import requests
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

mcp = FastMCP("GeneralByte Tools")

HA_URL = os.getenv("HA_URL", "http://homeassistant.local:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
DEFAULT_NOTIFY_SERVICE = "mobile_app_jeremys_iphone"

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}


def call_service(domain: str, service: str, data: dict) -> dict:
    """Call a Home Assistant service and return the JSON response."""
    url = f"{HA_URL}/api/services/{domain}/{service}"
    response = requests.post(url, headers=HEADERS, json=data, timeout=10)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {}


@mcp.tool
def send_phone_notification(message: str, title: str = "Notification", service: str | None = None) -> str:
    """Send a notification message to the configured phone via Home Assistant."""
    if not HA_TOKEN:
        return "Home Assistant token not configured"
    target_service = service or DEFAULT_NOTIFY_SERVICE
    call_service("notify", target_service, {"title": title, "message": message})
    return "Notification sent"


@mcp.tool
def get_todo_list(entity_id = "todo.todo", status: Optional[str] = None) -> dict:
    """Return items from a Home Assistant to-do list."""
    if not HA_TOKEN:
        return {"error": "Home Assistant token not configured"}
    
    # First, let's get all available todo entities
    url = f"{HA_URL}/api/states"
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    
    try:
        all_states = response.json()
        todo_entities = [state["entity_id"] for state in all_states if state["entity_id"].startswith("todo.")]
        
        if not todo_entities:
            return {"error": "No todo entities found in Home Assistant"}
        
        # If no specific entity_id provided or the provided one doesn't exist, use the first available
        if entity_id == "todo" or entity_id not in todo_entities:
            if entity_id != "todo":
                return {
                    "error": f"Todo entity '{entity_id}' not found. Available todo entities: {todo_entities}",
                    "available_entities": todo_entities
                }
            entity_id = todo_entities[0]
        
        # Now get the specific todo entity
        url = f"{HA_URL}/api/states/{entity_id}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        state_data = response.json()
        if state_data.get("state") == "unavailable":
            return {"error": f"Todo entity '{entity_id}' is unavailable"}
        
        # Extract items from the attributes
        items = state_data.get("attributes", {}).get("items", [])
        
        # Filter by status if specified
        if status:
            items = [item for item in items if item.get("status") == status]
        
        return {
            "entity_id": entity_id,
            "items": items,
            "total_items": len(items),
            "available_todo_entities": todo_entities
        }
    except ValueError:
        return {"error": "Invalid response from Home Assistant"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to Home Assistant: {str(e)}"}


@mcp.tool
def modify_todo_item(
    action: str,
    entity_id: str,
    item: Optional[str] = None,
    uid: Optional[str] = None,
    rename: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    due_datetime: Optional[str] = None,
) -> str:
    """Create, update or delete a to-do list item."""
    if not HA_TOKEN:
        return "Home Assistant token not configured"

    data = {"entity_id": entity_id}

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
            data["name"] = rename  # Changed from 'rename' to 'name'
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
        call_service("todo", service, data)
        return f"Todo item {action} successful"
    except requests.exceptions.HTTPError as e:
        return f"Failed to {action} todo item: {str(e)}"
