"""Tools for notifications and to-do lists via Home Assistant."""

import os
from typing import Optional

import requests
from fastmcp import FastMCP

mcp = FastMCP("GeneralByte Tools")

HA_URL = os.getenv("HA_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
DEFAULT_NOTIFY_SERVICE = os.getenv("HA_NOTIFY_SERVICE", "mobile_app_my_phone")

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
def send_phone_notification(message: str, service: str | None = None) -> str:
    """Send a notification message to the configured phone via Home Assistant."""
    if not HA_TOKEN:
        return "Home Assistant token not configured"
    target_service = service or DEFAULT_NOTIFY_SERVICE
    call_service("notify", target_service, {"message": message})
    return "Notification sent"


@mcp.tool
def get_todo_list(entity_id: str, status: Optional[str] = None) -> dict:
    """Return items from a Home Assistant to-do list."""
    if not HA_TOKEN:
        return {"error": "Home Assistant token not configured"}
    payload = {"entity_id": entity_id}
    if status:
        payload["status"] = [status]
    return call_service("todo", "get_items", payload)


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
            data["rename"] = rename
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

    call_service("todo", service, data)
    return f"Todo item {action} request sent"
