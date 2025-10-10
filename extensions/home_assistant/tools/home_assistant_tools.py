"""Home Assistant tools for Luna.

Control your local Home Assistant instance through natural language.
"""

from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any, List, Tuple

import requests
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# Load configuration from environment
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")
HA_REMOTE_ENTITY_ID = os.getenv("HA_REMOTE_ENTITY_ID", "remote.living_room_tv")

ALLOWED_DOMAINS: Tuple[str, ...] = (
    "light",
    "switch",
    "fan",
    "media_player",
)

SYSTEM_PROMPT = """You are an assistant with tools to control a local Home Assistant instance.

Translate natural-language requests into tool calls. Typical requests include turning entities on/off, 
checking an entity's state, or sending TV remote intents (e.g., launch an app, press HOME, PLAY, etc.). 
These tools operate over the Home Assistant HTTP API and expect HA_URL and HA_TOKEN environment variables 
to be set. Supported domains include light, switch, fan, and media_player.

When controlling the TV remote, provide a concise button/app token to the tool (e.g., "home", "play", 
"spotify", "open netflix"). Do NOT add device qualifiers like "on my tv" to the button value; the tool 
knows the target remote via HA_REMOTE_ENTITY_ID.

If the user asks to toggle something, first get the entity status and then make the correct change. 
Prefer friendly names over raw entity ids when possible.

Use these functions when appropriate:
- HA_GET_devices() to list devices
- HA_GET_entity_status(entity_id | friendly_name | entity_name) to get status
- HA_ACTION_turn_entity_on(entity_id | friendly_name | entity_name) to turn something on
- HA_ACTION_turn_entity_off(entity_id | friendly_name | entity_name) to turn something off
- HA_ACTION_tv_remote(button) to send remote intents or launch apps
"""


# Helper functions

def _headers() -> Dict[str, str]:
    """Return HTTP headers for Home Assistant API."""
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


def _require_config() -> Optional[str]:
    """Check that required environment variables are set."""
    if not HA_URL:
        return "Error: HA_URL environment variable not set! Please add it to your .env file."
    if not HA_TOKEN:
        return "Error: HA_TOKEN environment variable not set! Please add it to your .env file."
    return None


def _is_entity_id(identifier: str) -> bool:
    """Check if identifier is a valid entity_id format."""
    try:
        if not isinstance(identifier, str) or "." not in identifier:
            return False
        domain = identifier.split(".", 1)[0]
        return domain in ALLOWED_DOMAINS
    except Exception:
        return False


def _fetch_states() -> List[Dict[str, Any]]:
    """Fetch all entity states from Home Assistant."""
    url = f"{HA_URL}/api/states"
    response = requests.get(url, headers=_headers(), timeout=10)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    s = (text or "").strip().lower()
    return " ".join(s.split())


def _infer_domain_from_text(text: str) -> Optional[str]:
    """Infer Home Assistant domain from text description."""
    t = _normalize(text)
    if not t:
        return None
    if "light" in t or "lamp" in t or "bulb" in t:
        return "light"
    if "fan" in t:
        return "fan"
    if "switch" in t or "outlet" in t or "plug" in t or "relay" in t:
        return "switch"
    if "media player" in t or "tv" in t or "speaker" in t:
        return "media_player"
    return None


def _resolve_entity_id(entity_or_name: str, verify_exists: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a user-provided identifier to a concrete entity_id.
    
    Returns (entity_id, error). One of them will be None.
    """
    if not isinstance(entity_or_name, str) or not entity_or_name.strip():
        return None, "Invalid entity identifier"

    candidate = entity_or_name.strip()
    
    # If it's already an entity_id with an allowed domain
    if _is_entity_id(candidate):
        if not verify_exists or _entity_exists(candidate):
            return candidate, None
        # Try friendly fallback
        try:
            domain_hint = candidate.split(".", 1)[0]
        except Exception:
            domain_hint = None
        fallback_query = candidate.replace("_", " ").replace(".", " ")
        ent, err = _resolve_entity_id(fallback_query, verify_exists=False)
        if ent:
            return ent, None
        return None, f"Entity '{entity_or_name}' not found"

    # Try to resolve by friendly_name
    try:
        states = _fetch_states()
    except Exception as e:
        return None, f"Error loading entities: {str(e)}"

    target = _normalize(candidate)
    domain_filter = _infer_domain_from_text(candidate)
    
    def _allowed_for(df: Optional[str]) -> Optional[set[str]]:
        if not df:
            return None
        if df == "fan":
            return {"fan", "switch"}
        if df == "light":
            return {"light", "switch"}
        return {df}
    
    allowed = _allowed_for(domain_filter)
    matches: List[str] = []
    
    # Exact match first
    for st in states:
        try:
            ent = st.get("entity_id")
            if not isinstance(ent, str) or not ent:
                continue
            domain = ent.split(".", 1)[0]
            if domain not in ALLOWED_DOMAINS:
                continue
            if allowed and domain not in allowed:
                continue
            attrs = st.get("attributes", {}) if isinstance(st, dict) else {}
            fname = attrs.get("friendly_name")
            norm = _normalize(fname) if isinstance(fname, str) else ""
            if norm and norm == target:
                matches.append(ent)
        except Exception:
            continue

    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, (
            "Multiple entities match that friendly name: " + ", ".join(matches[:5]) +
            ("..." if len(matches) > 5 else "")
        )
    
    # Fallback to substring match
    partial_matches: List[str] = []
    for st in states:
        try:
            ent = st.get("entity_id")
            if not isinstance(ent, str) or not ent:
                continue
            domain = ent.split(".", 1)[0]
            if domain not in ALLOWED_DOMAINS:
                continue
            if allowed and domain not in allowed:
                continue
            fname = st.get("attributes", {}).get("friendly_name")
            norm = _normalize(fname) if isinstance(fname, str) else ""
            if norm and (target in norm or norm in target):
                partial_matches.append(ent)
        except Exception:
            continue
    
    if len(partial_matches) == 1:
        return partial_matches[0], None
    if len(partial_matches) > 1:
        return None, (
            "Multiple entities partially match that name: " + ", ".join(partial_matches[:5]) +
            ("..." if len(partial_matches) > 5 else "")
        )
    
    return None, f"Entity '{entity_or_name}' not found"


def _entity_exists(entity_id: str) -> bool:
    """Check if an entity exists in Home Assistant."""
    try:
        url = f"{HA_URL}/api/states/{entity_id}"
        resp = requests.get(url, headers=_headers(), timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _parse_tv_remote_intent(button: str) -> Tuple[str, Dict[str, Any], str]:
    """Parse a button string into Home Assistant remote service call."""
    b = (button or "").strip().lower()

    cmd_map: Dict[str, str] = {
        "up": "DPAD_UP",
        "down": "DPAD_DOWN",
        "left": "DPAD_LEFT",
        "right": "DPAD_RIGHT",
        "ok": "DPAD_CENTER",
        "enter": "DPAD_CENTER",
        "select": "DPAD_CENTER",
        "center": "DPAD_CENTER",
        "back": "BACK",
        "home": "HOME",
        "play": "MEDIA_PLAY_PAUSE",
        "pause": "MEDIA_PLAY_PAUSE",
        "play/pause": "MEDIA_PLAY_PAUSE",
        "stop": "MEDIA_STOP",
        "next": "MEDIA_NEXT",
        "previous": "MEDIA_PREVIOUS",
        "prev": "MEDIA_PREVIOUS",
        "rewind": "MEDIA_REWIND",
        "fast forward": "MEDIA_FAST_FORWARD",
        "ff": "MEDIA_FAST_FORWARD",
        "mute": "MUTE",
        "volume up": "VOLUME_UP",
        "vol up": "VOLUME_UP",
        "volume down": "VOLUME_DOWN",
        "vol down": "VOLUME_DOWN",
    }

    app_map: Dict[str, str] = {
        "youtube": "https://www.youtube.com",
        "netflix": "com.netflix.ninja",
        "spotify": "com.spotify.tv.android",
        "disney": "com.disney.disneyplus",
        "disney+": "com.disney.disneyplus",
    }

    # Handle "open <app>" or "launch <app>"
    if b.startswith("open ") or b.startswith("launch "):
        b2 = b.split(" ", 1)[1].strip()
        activity = app_map.get(b2, b2)
        return (
            "turn_on",
            {"entity_id": HA_REMOTE_ENTITY_ID, "activity": activity},
            f"open {b2}",
        )

    # Direct app names
    if b in app_map:
        return (
            "turn_on",
            {"entity_id": HA_REMOTE_ENTITY_ID, "activity": app_map[b]},
            b,
        )

    # URLs or package names
    if b.startswith("http://") or b.startswith("https://") or ("." in b and " " not in b and b not in cmd_map):
        return (
            "turn_on",
            {"entity_id": HA_REMOTE_ENTITY_ID, "activity": button.strip()},
            button.strip(),
        )

    # Commands
    code = cmd_map.get(b)
    if code is None:
        code = button.strip().upper()
    
    return (
        "send_command",
        {"entity_id": HA_REMOTE_ENTITY_ID, "command": code},
        code,
    )


# Tool Args classes

class HA_GET_DevicesArgs(BaseModel):
    """No arguments required for listing devices."""
    pass


class HA_GET_EntityStatusArgs(BaseModel):
    """Arguments for getting entity status."""
    entity_id: Optional[str] = Field(None, description="Entity ID (e.g. 'light.kitchen')")
    friendly_name: Optional[str] = Field(None, description="Friendly name (e.g. 'Kitchen Light')")
    entity_name: Optional[str] = Field(None, description="Entity name (alias for friendly_name)")


class HA_ACTION_TurnEntityOnArgs(BaseModel):
    """Arguments for turning an entity on."""
    entity_id: Optional[str] = Field(None, description="Entity ID (e.g. 'light.kitchen')")
    friendly_name: Optional[str] = Field(None, description="Friendly name (e.g. 'Kitchen Light')")
    entity_name: Optional[str] = Field(None, description="Entity name (alias for friendly_name)")


class HA_ACTION_TurnEntityOffArgs(BaseModel):
    """Arguments for turning an entity off."""
    entity_id: Optional[str] = Field(None, description="Entity ID (e.g. 'light.kitchen')")
    friendly_name: Optional[str] = Field(None, description="Friendly name (e.g. 'Kitchen Light')")
    entity_name: Optional[str] = Field(None, description="Entity name (alias for friendly_name)")


class HA_ACTION_TvRemoteArgs(BaseModel):
    """Arguments for TV remote control."""
    button: str = Field(..., description="Button/command/app to send (e.g. 'home', 'play', 'open netflix')")


# Rebuild models to ensure all forward references are resolved
HA_GET_DevicesArgs.model_rebuild()
HA_GET_EntityStatusArgs.model_rebuild()
HA_ACTION_TurnEntityOnArgs.model_rebuild()
HA_ACTION_TurnEntityOffArgs.model_rebuild()
HA_ACTION_TvRemoteArgs.model_rebuild()


# Tool functions

def HA_GET_devices() -> Tuple[bool, str]:
    """Get list of all available Home Assistant devices and their current states.
    Example Prompt: list my home devices
    Example Response: {"devices": [{"entity_id": "light.kitchen", "domain": "light", "state": "off", "friendly_name": "Kitchen Light"}]}
    Example Args: {}
    Notes: Includes each entity's entity_id, domain, current state, and friendly_name.
    """
    try:
        _ = HA_GET_DevicesArgs()
    except Exception as e:
        return (False, f"Validation error: {e}")
    
    err = _require_config()
    if err:
        return (False, err)
    
    try:
        url = f"{HA_URL}/api/states"
        response = requests.get(url, headers=_headers(), timeout=10)
        response.raise_for_status()
        states = response.json()
        
        devices = []
        for state in states:
            try:
                ent = state.get("entity_id")
                if isinstance(ent, str) and ent.split(".", 1)[0] in ALLOWED_DOMAINS:
                    attrs = state.get("attributes", {}) if isinstance(state, dict) else {}
                    devices.append({
                        "entity_id": ent,
                        "state": state.get("state"),
                        "domain": ent.split(".")[0],
                        "friendly_name": attrs.get("friendly_name", ent),
                    })
            except Exception:
                continue
        
        return (True, json.dumps({"devices": devices}))
    except Exception as e:
        return (False, f"Error listing devices: {str(e)}")


def HA_GET_entity_status(entity_id: Optional[str] = None, friendly_name: Optional[str] = None, 
                         entity_name: Optional[str] = None) -> Tuple[bool, str]:
    """Get status of a specific Home Assistant entity.
    Example Prompt: what's the status of the living room light?
    Example Response: {"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 200}}
    Example Args: {"entity_id": "light.kitchen"} or {"friendly_name": "Kitchen Light"}
    Notes: Accepts either a full entity_id or a friendly_name. Also accepts entity_name as an alias.
    """
    try:
        _ = HA_GET_EntityStatusArgs(
            entity_id=entity_id,
            friendly_name=friendly_name,
            entity_name=entity_name
        )
    except Exception as e:
        return (False, f"Validation error: {e}")
    
    err = _require_config()
    if err:
        return (False, err)
    
    identifier = entity_id or friendly_name or entity_name
    if not isinstance(identifier, str) or not identifier.strip():
        return (False, "Missing 'entity_id' or 'friendly_name'")
    
    resolved, rerr = _resolve_entity_id(identifier)
    if rerr:
        return (False, rerr)
    
    entity_id = resolved or identifier
    
    try:
        url = f"{HA_URL}/api/states/{entity_id}"
        response = requests.get(url, headers=_headers(), timeout=10)
        if response.status_code == 404:
            return (False, f"Entity '{entity_id}' not found")
        response.raise_for_status()
        state = response.json()
        
        result = {
            "entity_id": state.get("entity_id", entity_id),
            "state": state.get("state"),
            "attributes": state.get("attributes", {}),
        }
        return (True, json.dumps(result))
    except Exception as e:
        return (False, f"Error getting entity status: {str(e)}")


def HA_ACTION_turn_entity_on(entity_id: Optional[str] = None, friendly_name: Optional[str] = None,
                              entity_name: Optional[str] = None) -> Tuple[bool, str]:
    """Turn on a specific Home Assistant entity.
    Example Prompt: turn on the kitchen light
    Example Response: {"success": true, "message": "Successfully turned on 'light.kitchen'"}
    Example Args: {"entity_id": "light.kitchen"} or {"friendly_name": "Kitchen Light"}
    Notes: Accepts either entity_id or friendly_name. Also accepts entity_name as an alias.
    """
    try:
        _ = HA_ACTION_TurnEntityOnArgs(
            entity_id=entity_id,
            friendly_name=friendly_name,
            entity_name=entity_name
        )
    except Exception as e:
        return (False, f"Validation error: {e}")
    
    err = _require_config()
    if err:
        return (False, err)
    
    identifier = entity_id or friendly_name or entity_name
    if not isinstance(identifier, str) or not identifier.strip():
        return (False, "Missing 'entity_id' or 'friendly_name'")
    
    resolved, rerr = _resolve_entity_id(identifier)
    if rerr:
        return (False, rerr)
    
    entity_id = resolved or identifier
    
    try:
        domain = entity_id.split(".")[0]
        if not _entity_exists(entity_id):
            return (False, f"Entity '{entity_id}' not found")
        
        service_url = f"{HA_URL}/api/services/{domain}/turn_on"
        response = requests.post(service_url, headers=_headers(), json={"entity_id": entity_id}, timeout=10)
        response.raise_for_status()
        
        result = {
            "success": True,
            "message": f"Successfully turned on '{entity_id}'"
        }
        return (True, json.dumps(result))
    except Exception as e:
        return (False, f"Error turning on {entity_id}: {str(e)}")


def HA_ACTION_turn_entity_off(entity_id: Optional[str] = None, friendly_name: Optional[str] = None,
                               entity_name: Optional[str] = None) -> Tuple[bool, str]:
    """Turn off a specific Home Assistant entity.
    Example Prompt: turn off the kitchen light
    Example Response: {"success": true, "message": "Successfully turned off 'light.kitchen'"}
    Example Args: {"entity_id": "light.kitchen"} or {"friendly_name": "Kitchen Light"}
    Notes: Accepts either entity_id or friendly_name. Also accepts entity_name as an alias.
    """
    try:
        _ = HA_ACTION_TurnEntityOffArgs(
            entity_id=entity_id,
            friendly_name=friendly_name,
            entity_name=entity_name
        )
    except Exception as e:
        return (False, f"Validation error: {e}")
    
    err = _require_config()
    if err:
        return (False, err)
    
    identifier = entity_id or friendly_name or entity_name
    if not isinstance(identifier, str) or not identifier.strip():
        return (False, "Missing 'entity_id' or 'friendly_name'")
    
    resolved, rerr = _resolve_entity_id(identifier)
    if rerr:
        return (False, rerr)
    
    entity_id = resolved or identifier
    
    try:
        domain = entity_id.split(".")[0]
        if not _entity_exists(entity_id):
            return (False, f"Entity '{entity_id}' not found")
        
        service_url = f"{HA_URL}/api/services/{domain}/turn_off"
        response = requests.post(service_url, headers=_headers(), json={"entity_id": entity_id}, timeout=10)
        response.raise_for_status()
        
        result = {
            "success": True,
            "message": f"Successfully turned off '{entity_id}'"
        }
        return (True, json.dumps(result))
    except Exception as e:
        return (False, f"Error turning off {entity_id}: {str(e)}")


def HA_ACTION_tv_remote(button: str) -> Tuple[bool, str]:
    """Send a TV remote action or launch an app.
    Example Prompt: open spotify on my tv
    Example Response: {"success": true, "message": "Sent 'spotify' to remote.living_room_tv"}
    Example Args: {"button": "home"} or {"button": "open netflix"} or {"button": "spotify"}
    Notes: Accepts navigation commands (up, down, home, back), playback controls (play, pause, stop), 
    volume controls (mute, volume up, volume down), app names (youtube, netflix, spotify, disney+), 
    or raw Android TV keycodes. Target remote is configured via HA_REMOTE_ENTITY_ID env var.
    """
    try:
        _ = HA_ACTION_TvRemoteArgs(button=button)
    except Exception as e:
        return (False, f"Validation error: {e}")
    
    err = _require_config()
    if err:
        return (False, err)
    
    if not _entity_exists(HA_REMOTE_ENTITY_ID):
        return (False, f"Remote entity '{HA_REMOTE_ENTITY_ID}' not found. Set HA_REMOTE_ENTITY_ID in .env")
    
    service, payload, label = _parse_tv_remote_intent(button)
    
    try:
        if service == "turn_on":
            svc_url = f"{HA_URL}/api/services/remote/turn_on"
        else:
            svc_url = f"{HA_URL}/api/services/remote/send_command"
        
        response = requests.post(svc_url, headers=_headers(), json=payload, timeout=10)
        response.raise_for_status()
        
        result = {
            "success": True,
            "message": f"Sent '{label}' to {HA_REMOTE_ENTITY_ID}"
        }
        return (True, json.dumps(result))
    except Exception as e:
        return (False, f"Error sending '{label}' to {HA_REMOTE_ENTITY_ID}: {str(e)}")


# Export tools list
TOOLS = [
    HA_GET_devices,
    HA_GET_entity_status,
    HA_ACTION_turn_entity_on,
    HA_ACTION_turn_entity_off,
    HA_ACTION_tv_remote,
]

