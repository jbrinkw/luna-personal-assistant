"""Local Home Assistant tools (no MCP decorators).

These mirror the functions exposed by the Home Assistant MCP server,
but are safe to import and call directly.
"""

from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any, List

import requests
try:
    from dotenv import load_dotenv  # pragma: no cover
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


HA_URL = os.getenv("HA_URL", "http://192.168.0.216:8123")
HA_TOKEN = os.getenv("HA_TOKEN")


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


def _require_token() -> Optional[str]:
    if not HA_TOKEN:
        return "Error: HA_TOKEN environment variable not set!"
    return None


def HA_GET_devices() -> str:
    """Get list of all available Home Assistant devices and their current states."""
    err = _require_token()
    if err:
        return err
    try:
        url = f"{HA_URL}/api/states"
        response = requests.get(url, headers=_headers(), timeout=10)
        response.raise_for_status()
        states = response.json()
        devices: List[Dict[str, Any]] = []
        for state in states:
            try:
                ent = state.get("entity_id")
                if isinstance(ent, str) and ent.startswith(("light.", "switch.", "fan.", "media_player.")):
                    attrs = state.get("attributes", {}) if isinstance(state, dict) else {}
                    devices.append(
                        {
                            "entity_id": ent,
                            "state": state.get("state"),
                            "domain": ent.split(".")[0],
                            "friendly_name": attrs.get("friendly_name", ent),
                        }
                    )
            except Exception:
                continue
        return json.dumps(devices, indent=2)
    except Exception as e:  # pragma: no cover - best-effort
        return f"Error listing devices: {str(e)}"


def HA_GET_entity_status(entity_id: str) -> str:
    """Get status of a specific Home Assistant entity by entity ID."""
    err = _require_token()
    if err:
        return err
    try:
        url = f"{HA_URL}/api/states/{entity_id}"
        response = requests.get(url, headers=_headers(), timeout=10)
        if response.status_code == 404:
            return f"Entity '{entity_id}' not found"
        response.raise_for_status()
        state = response.json()
        return json.dumps(
            {
                "entity_id": state.get("entity_id", entity_id),
                "state": state.get("state"),
                "attributes": state.get("attributes", {}),
            },
            indent=2,
        )
    except Exception as e:  # pragma: no cover - best-effort
        return f"Error getting entity status: {str(e)}"


def HA_ACTION_turn_entity_on(entity_id: str) -> str:
    """Turn on a specific Home Assistant entity by entity ID."""
    err = _require_token()
    if err:
        return err
    try:
        domain = entity_id.split(".")[0]
        service_url = f"{HA_URL}/api/services/{domain}/turn_on"
        response = requests.post(service_url, headers=_headers(), json={"entity_id": entity_id}, timeout=10)
        response.raise_for_status()
        return f"Successfully turned on '{entity_id}'"
    except Exception as e:  # pragma: no cover
        return f"Error turning on {entity_id}: {str(e)}"


def HA_ACTION_turn_entity_off(entity_id: str) -> str:
    """Turn off a specific Home Assistant entity by entity ID."""
    err = _require_token()
    if err:
        return err
    try:
        domain = entity_id.split(".")[0]
        service_url = f"{HA_URL}/api/services/{domain}/turn_off"
        response = requests.post(service_url, headers=_headers(), json={"entity_id": entity_id}, timeout=10)
        response.raise_for_status()
        return f"Successfully turned off '{entity_id}'"
    except Exception as e:  # pragma: no cover
        return f"Error turning off {entity_id}: {str(e)}"



