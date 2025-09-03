"""Local Home Assistant tools (no MCP decorators).

These mirror the functions exposed by the Home Assistant MCP server,
but are safe to import and call directly.
"""

from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any, List, Tuple

import requests
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
    """Send a TV remote action by name (single string).

    Examples: 'up', 'down', 'left', 'right', 'ok', 'back', 'home',
    'play', 'pause', 'stop', 'next', 'previous', 'rewind', 'fast forward',
    'mute', 'volume up', 'volume down', 'youtube', 'netflix', 'spotify', 'disney+'.

    Also accepts raw activity strings (e.g., 'https://www.youtube.com', 'com.spotify.tv.android')
    and raw command codes (e.g., 'DPAD_UP'). Uses HA_REMOTE_ENTITY_ID if set, otherwise
    defaults to 'remote.living_room_tv'.
    """
    err = _require_token()
    if err:
        return err
    remote_entity = _get_remote_entity_id()
    if not _entity_exists(remote_entity):
        return f"Remote entity '{remote_entity}' not found"
    service, payload, label = _parse_tv_remote_intent(button)
    try:
        if service == "turn_on":
            svc_url = f"{HA_URL}/api/services/remote/turn_on"
        else:
            svc_url = f"{HA_URL}/api/services/remote/send_command"
        response = requests.post(svc_url, headers=_headers(), json=payload, timeout=10)
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = None
        # Remote services often return an empty list even when successful; treat HTTP 200 as success
        if isinstance(data, list) and len(data) == 0:
            return f"Sent '{label}' to {remote_entity}"
        return f"Sent '{label}' to {remote_entity}"
    except Exception as e:  # pragma: no cover
        return f"Error sending '{label}' to {remote_entity}: {str(e)}"


def HA_GET_devices() -> str:
    """Get list of all available Home Assistant devices and their current states.

    Includes each entity's `entity_id`, `domain`, current `state`, and `friendly_name`.
    """
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
                if isinstance(ent, str) and ent.split(".", 1)[0] in ALLOWED_DOMAINS:
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
    """Get status of a specific Home Assistant entity.

    Accepts either a full `entity_id` (e.g. 'light.living_room') or a `friendly name`
    (e.g. 'Living Room Light').
    """
    err = _require_token()
    if err:
        return err
    resolved, rerr = _resolve_entity_id(entity_id)
    if rerr:
        return rerr
    entity_id = resolved or entity_id
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
    """Turn on a specific Home Assistant entity.

    Accepts either a full `entity_id` (e.g. 'light.kitchen') or a `friendly name`
    (e.g. 'Kitchen Light'). Returns a clear message if the entity does not exist
    or if Home Assistant reports no changes.
    """
    err = _require_token()
    if err:
        return err
    resolved, rerr = _resolve_entity_id(entity_id)
    if rerr:
        return rerr
    entity_id = resolved or entity_id
    try:
        domain = entity_id.split(".")[0]
        # Validate existence to avoid returning success on no-op
        if not _entity_exists(entity_id):
            return f"Entity '{entity_id}' not found"
        service_url = f"{HA_URL}/api/services/{domain}/turn_on"
        response = requests.post(service_url, headers=_headers(), json={"entity_id": entity_id}, timeout=10)
        response.raise_for_status()
        # Many HA service calls return a list of affected state objects; treat empty as no-op
        try:
            data = response.json()
        except Exception:
            data = None
        if isinstance(data, list) and len(data) == 0:
            return f"No changes reported by Home Assistant for '{entity_id}'"
        return f"Successfully turned on '{entity_id}'"
    except Exception as e:  # pragma: no cover
        return f"Error turning on {entity_id}: {str(e)}"


def HA_ACTION_turn_entity_off(entity_id: str) -> str:
    """Turn off a specific Home Assistant entity.

    Accepts either a full `entity_id` (e.g. 'light.kitchen') or a `friendly name`
    (e.g. 'Kitchen Light'). Returns a clear message if the entity does not exist
    or if Home Assistant reports no changes.
    """
    err = _require_token()
    if err:
        return err
    resolved, rerr = _resolve_entity_id(entity_id)
    if rerr:
        return rerr
    entity_id = resolved or entity_id
    try:
        domain = entity_id.split(".")[0]
        # Validate existence to avoid returning success on no-op
        if not _entity_exists(entity_id):
            return f"Entity '{entity_id}' not found"
        service_url = f"{HA_URL}/api/services/{domain}/turn_off"
        response = requests.post(service_url, headers=_headers(), json={"entity_id": entity_id}, timeout=10)
        response.raise_for_status()
        try:
            data = response.json()
        except Exception:
            data = None
        if isinstance(data, list) and len(data) == 0:
            return f"No changes reported by Home Assistant for '{entity_id}'"
        return f"Successfully turned off '{entity_id}'"
    except Exception as e:  # pragma: no cover
        return f"Error turning off {entity_id}: {str(e)}"



