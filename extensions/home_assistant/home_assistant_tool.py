"""Local Home Assistant tools (no MCP decorators).

Example prompt: "open spotify on my tv"

These mirror the functions exposed by the Home Assistant MCP server,
but are safe to import and call directly.
"""

from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any, List, Tuple

import requests
from pydantic import BaseModel, Field
try:
    from dotenv import load_dotenv  # pragma: no cover
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


HA_URL = os.getenv("HA_URL", "http://192.168.0.216:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
ALLOWED_DOMAINS: Tuple[str, ...] = (
    "light",
    "switch",
    "fan",
    "media_player",
)

SYSTEM_PROMPT = """
You are an assistant with tools to control a local Home Assistant instance.

Translate natural-language requests into tool calls. Typical requests include
turning entities on/off, checking an entity's state, or sending TV remote
intents (e.g., launch an app, press HOME, PLAY, etc.). These tools operate over
the Home Assistant HTTP API and expect HA_URL and HA_TOKEN environment variables
to be set. Supported domains include light, switch, fan, and media_player.

When controlling the TV remote, provide a concise button/app token to the tool
(e.g., "home", "play", "spotify", "open netflix"). Do NOT add device qualifiers
like "on my tv" to the button value; the tool knows the target remote via
HA_REMOTE_ENTITY_ID (default: remote.living_room_tv).

If the user asks to toggle something, first get the entity status and then make
the correct change. Prefer friendly names over raw entity ids when possible.

Use these functions when appropriate:
- HA_GET_devices() to list devices
- HA_GET_entity_status(entity_id | friendly_name | entity_name) to get status
- HA_ACTION_turn_entity_on(entity_id | friendly_name | entity_name) to turn something on
- HA_ACTION_turn_entity_off(entity_id | friendly_name | entity_name) to turn something off
- HA_ACTION_tv_remote(button) to send remote intents or launch apps
"""


class OperationResult(BaseModel):
    success: bool
    message: str


class Device(BaseModel):
    entity_id: str
    domain: str
    state: Optional[str] = None
    friendly_name: Optional[str] = None


class DevicesResponse(BaseModel):
    devices: list[Device] = Field(default_factory=list)


class EntityStatus(BaseModel):
    entity_id: str
    state: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)

# Ensure any forward refs are resolved under postponed annotations
OperationResult.model_rebuild()
Device.model_rebuild()
DevicesResponse.model_rebuild()
EntityStatus.model_rebuild()


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


def _require_token() -> Optional[str]:
    if not HA_TOKEN:
        return "Error: HA_TOKEN environment variable not set!"
    return None


def _is_entity_id(identifier: str) -> bool:
    try:
        if not isinstance(identifier, str) or "." not in identifier:
            return False
        domain = identifier.split(".", 1)[0]
        return domain in ALLOWED_DOMAINS
    except Exception:
        return False


def _fetch_states() -> List[Dict[str, Any]]:
    url = f"{HA_URL}/api/states"
    response = requests.get(url, headers=_headers(), timeout=10)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _normalize(text: str) -> str:
    s = (text or "").strip().lower()
    # collapse spaces
    return " ".join(s.split())


def _infer_domain_from_text(text: str) -> Optional[str]:
    t = _normalize(text)
    if not t:
        return None
    # simple keyword-based domain inference
    if "light" in t or "lamp" in t or "bulb" in t:
        return "light"
    if "fan" in t:
        # Many fans are exposed as switch.* in HA ecosystems (e.g., Shelly)
        return "fan"
    if "switch" in t or "outlet" in t or "plug" in t or "relay" in t:
        return "switch"
    if "media player" in t or "tv" in t or "speaker" in t:
        return "media_player"
    return None


def _resolve_entity_id(entity_or_name: str, verify_exists: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a user-provided identifier to a concrete entity_id.

    Accepts either a full entity_id (e.g. 'light.kitchen') or a friendly name
    (e.g. 'Kitchen Light'). Returns (entity_id, error). One of them will be None.
    """
    if not isinstance(entity_or_name, str) or not entity_or_name.strip():
        return None, "Invalid entity identifier"

    # If it's already an entity_id with an allowed domain, use it as-is
    candidate = entity_or_name.strip()
    if _is_entity_id(candidate):
        # Optionally verify existence; if not found, try friendly fallback
        if not verify_exists or _entity_exists(candidate):
            return candidate, None
        # derive a friendly-like query from candidate, e.g. 'fan.living_room' -> 'living room'
        try:
            domain_hint = candidate.split(".", 1)[0]
        except Exception:
            domain_hint = None
        fallback_query = candidate.replace("_", " ").replace(".", " ")
        # try friendly resolution using derived query and domain hint
        ent, err = _resolve_entity_id(fallback_query, verify_exists=False)  # type: ignore[misc]
        if ent:
            return ent, None
        # keep the original not-found error for clarity
        return None, f"Entity '{entity_or_name}' not found"

    # Otherwise, try to resolve by friendly_name across allowed domains
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
            # exact match first
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
    # fallback to substring contains match if no exact match
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
    try:
        url = f"{HA_URL}/api/states/{entity_id}"
        resp = requests.get(url, headers=_headers(), timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _get_remote_entity_id() -> str:
    rid = os.getenv("HA_REMOTE_ENTITY_ID")
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    return "remote.living_room_tv"


def _parse_tv_remote_intent(button: str) -> Tuple[str, Dict[str, Any], str]:
    b = (button or "").strip().lower()
    remote_entity = _get_remote_entity_id()

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

    label = button.strip()

    if b.startswith("open ") or b.startswith("launch "):
        b2 = b.split(" ", 1)[1].strip()
        activity = app_map.get(b2, b2)
        return (
            "turn_on",
            {"entity_id": remote_entity, "activity": activity},
            f"open {b2}",
        )

    if b in app_map:
        return (
            "turn_on",
            {"entity_id": remote_entity, "activity": app_map[b]},
            b,
        )

    if b.startswith("http://") or b.startswith("https://") or ("." in b and " " not in b and b not in cmd_map):
        return (
            "turn_on",
            {"entity_id": remote_entity, "activity": button.strip()},
            button.strip(),
        )

    # commands (map synonyms or accept raw codes)
    code = cmd_map.get(b)
    if code is None:
        # attempt raw code from user by uppercasing
        code = button.strip().upper()
    return (
        "send_command",
        {"entity_id": remote_entity, "command": code},
        code,
    )


def HA_ACTION_tv_remote(button: str) -> str:
    """Send a TV remote action or launch an app.

    Required env: HA_URL, HA_TOKEN. Target remote entity is HA_REMOTE_ENTITY_ID
    if set, else defaults to 'remote.living_room_tv'.

    Args:
      - button: a concise action/app token. Avoid device qualifiers like
        "on my tv"; the tool already knows the target remote. Accepted forms:
        - Navigation/controls: 'up', 'down', 'left', 'right', 'ok', 'back',
          'home', 'play', 'pause', 'stop', 'next', 'previous', 'rewind',
          'fast forward', 'mute', 'volume up', 'volume down'
        - Apps (mapped automatically): 'youtube', 'netflix', 'spotify', 'disney+'
        - Open/launch phrasing also works: 'open youtube', 'open spotify', etc.
        - Raw activity strings: 'https://www.youtube.com', 'com.spotify.tv.android'
        - Raw command codes: 'DPAD_UP', 'MEDIA_PLAY_PAUSE', etc.

    Behavior:
      - App tokens or 'open <app>' → remote.turn_on with payload {activity}
        Examples:
          - button='spotify' → activity='com.spotify.tv.android'
          - button='open youtube' → activity='https://www.youtube.com'
      - Control tokens → remote.send_command with payload {command}
        Examples:
          - button='home' → command='HOME'
          - button='play' → command='MEDIA_PLAY_PAUSE'

    Returns: OperationResult JSON string with {success: bool, message: str}

    Examples:
      - {"button": "home"}
      - {"button": "open netflix"}
      - {"button": "spotify"}
    """
    err = _require_token()
    if err:
        return OperationResult(success=False, message=err)
    remote_entity = _get_remote_entity_id()
    if not _entity_exists(remote_entity):
        return OperationResult(success=False, message=f"Remote entity '{remote_entity}' not found")
    service, payload, label = _parse_tv_remote_intent(button)
    try:
        if service == "turn_on":
            svc_url = f"{HA_URL}/api/services/remote/turn_on"
        else:
            svc_url = f"{HA_URL}/api/services/remote/send_command"
        response = requests.post(svc_url, headers=_headers(), json=payload, timeout=10)
        response.raise_for_status()
        # Treat HTTP 200 as success regardless of body
        return OperationResult(success=True, message=f"Sent '{label}' to {remote_entity}")
    except Exception as e:  # pragma: no cover
        return OperationResult(success=False, message=f"Error sending '{label}' to {remote_entity}: {str(e)}")


def HA_GET_devices() -> DevicesResponse | OperationResult:
    """Get list of all available Home Assistant devices and their current states.
    Example Prompt: "list my home devices"
    Example Response: {"devices": [{"entity_id": "light.kitchen", "domain": "light", "state": "off", "friendly_name": "Kitchen Light"}]}
    Example Args: {}
    Includes each entity's `entity_id`, `domain`, current `state`, and `friendly_name`.
    """
    err = _require_token()
    if err:
        return OperationResult(success=False, message=err)
    try:
        url = f"{HA_URL}/api/states"
        response = requests.get(url, headers=_headers(), timeout=10)
        response.raise_for_status()
        states = response.json()
        devices: List[Device] = []
        for state in states:
            try:
                ent = state.get("entity_id")
                if isinstance(ent, str) and ent.split(".", 1)[0] in ALLOWED_DOMAINS:
                    attrs = state.get("attributes", {}) if isinstance(state, dict) else {}
                    devices.append(Device(
                        entity_id=ent,
                        state=state.get("state"),
                        domain=ent.split(".")[0],
                        friendly_name=attrs.get("friendly_name", ent),
                    ))
            except Exception:
                continue
        return DevicesResponse(devices=devices)
    except Exception as e:  # pragma: no cover - best-effort
        return OperationResult(success=False, message=f"Error listing devices: {str(e)}")


def HA_GET_entity_status(entity_id: Optional[str] = None, friendly_name: Optional[str] = None, entity_name: Optional[str] = None) -> EntityStatus | OperationResult:
    """Get status of a specific Home Assistant entity.
    Example Prompt: "what's the status of the living room light?"
    Example Response: {"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 200}}
    Example Args: {"entity_id": "string[entity id]"} or {"friendly_name": "string[name]"}
    Accepts either a full `entity_id` (e.g. 'switch.living_room_light') or a `friendly_name`
    (e.g. 'Living Room Light'). Also accepts `entity_name` as an alias for `friendly_name`.
    """
    err = _require_token()
    if err:
        return OperationResult(success=False, message=err)
    identifier = entity_id or friendly_name or entity_name
    if not isinstance(identifier, str) or not identifier.strip():
        return OperationResult(success=False, message="Missing 'entity_id' or 'friendly_name'")
    resolved, rerr = _resolve_entity_id(identifier)
    if rerr:
        return OperationResult(success=False, message=rerr)
    entity_id = resolved or identifier
    try:
        url = f"{HA_URL}/api/states/{entity_id}"
        response = requests.get(url, headers=_headers(), timeout=10)
        if response.status_code == 404:
            return OperationResult(success=False, message=f"Entity '{entity_id}' not found")
        response.raise_for_status()
        state = response.json()
        return EntityStatus(
            entity_id=state.get("entity_id", entity_id),
            state=state.get("state"),
            attributes=state.get("attributes", {}),
        )
    except Exception as e:  # pragma: no cover - best-effort
        return OperationResult(success=False, message=f"Error getting entity status: {str(e)}")


def HA_ACTION_turn_entity_on(entity_id: Optional[str] = None, friendly_name: Optional[str] = None, entity_name: Optional[str] = None) -> OperationResult:
    """Turn on a specific Home Assistant entity.
    Example Prompt: "turn on the kitchen light"
    Example Response: {"success": true, "message": "Successfully turned on 'light.kitchen'"}
    Example Args: {"entity_id": "string[entity id]"} or {"friendly_name": "string[name]"}
    Accepts either a full `entity_id` (e.g. 'light.kitchen') or a `friendly_name`
    (e.g. 'Kitchen Light'). Also accepts `entity_name` as an alias for `friendly_name`. Returns a clear message if the entity does not exist
    or if Home Assistant reports no changes.
    """
    err = _require_token()
    if err:
        return OperationResult(success=False, message=err)
    identifier = entity_id or friendly_name or entity_name
    if not isinstance(identifier, str) or not identifier.strip():
        return OperationResult(success=False, message="Missing 'entity_id' or 'friendly_name'")
    resolved, rerr = _resolve_entity_id(identifier)
    if rerr:
        return OperationResult(success=False, message=rerr)
    entity_id = resolved or identifier
    try:
        domain = entity_id.split(".")[0]
        # Validate existence to avoid returning success on no-op
        if not _entity_exists(entity_id):
            return OperationResult(success=False, message=f"Entity '{entity_id}' not found")
        service_url = f"{HA_URL}/api/services/{domain}/turn_on"
        response = requests.post(service_url, headers=_headers(), json={"entity_id": entity_id}, timeout=10)
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = None
        if isinstance(data, list) and len(data) == 0:
            return OperationResult(success=True, message=f"No changes reported by Home Assistant for '{entity_id}'")
        return OperationResult(success=True, message=f"Successfully turned on '{entity_id}'")
    except Exception as e:  # pragma: no cover
        return OperationResult(success=False, message=f"Error turning on {entity_id}: {str(e)}")


def HA_ACTION_turn_entity_off(entity_id: Optional[str] = None, friendly_name: Optional[str] = None, entity_name: Optional[str] = None) -> OperationResult:
    """Turn off a specific Home Assistant entity.
    Example Prompt: "turn off the kitchen light"
    Example Response: {"success": true, "message": "Successfully turned off 'light.kitchen'"}
    Example Args: {"entity_id": "string[entity id]"} or {"friendly_name": "string[name]"}
    Accepts either a full `entity_id` (e.g. 'light.kitchen') or a `friendly_name`
    (e.g. 'Kitchen Light'). Also accepts `entity_name` as an alias for `friendly_name`. Returns a clear message if the entity does not exist
    or if Home Assistant reports no changes.
    """
    err = _require_token()
    if err:
        return OperationResult(success=False, message=err)
    identifier = entity_id or friendly_name or entity_name
    if not isinstance(identifier, str) or not identifier.strip():
        return OperationResult(success=False, message="Missing 'entity_id' or 'friendly_name'")
    resolved, rerr = _resolve_entity_id(identifier)
    if rerr:
        return OperationResult(success=False, message=rerr)
    entity_id = resolved or identifier
    try:
        domain = entity_id.split(".")[0]
        # Validate existence to avoid returning success on no-op
        if not _entity_exists(entity_id):
            return OperationResult(success=False, message=f"Entity '{entity_id}' not found")
        service_url = f"{HA_URL}/api/services/{domain}/turn_off"
        response = requests.post(service_url, headers=_headers(), json={"entity_id": entity_id}, timeout=10)
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = None
        if isinstance(data, list) and len(data) == 0:
            return OperationResult(success=True, message=f"No changes reported by Home Assistant for '{entity_id}'")
        return OperationResult(success=True, message=f"Successfully turned off '{entity_id}'")
    except Exception as e:  # pragma: no cover
        return OperationResult(success=False, message=f"Error turning off {entity_id}: {str(e)}")


NAME = "Home Assistant"

TOOLS = [
    HA_GET_devices,
    HA_GET_entity_status,
    HA_ACTION_turn_entity_on,
    HA_ACTION_turn_entity_off,
    HA_ACTION_tv_remote,
]


