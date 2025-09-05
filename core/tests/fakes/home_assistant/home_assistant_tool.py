"""Auto-generated fake tool module. Do not edit by hand.

This module mirrors function names, signatures, and docstrings from the
original tool, but contains no operational code. All functions return None.
"""
from __future__ import annotations

NAME = 'Home Assistant'
SYSTEM_PROMPT = '\nYou are an assistant with tools to control a local Home Assistant instance.\n\nYour job is to translate natural-language requests into precise tool calls\nto query device status or perform actions. Typical requests include things like\nturning entities on or off, checking an entity\'s state, or sending TV remote\nintents (e.g., "open spotify on my tv"). These tools operate over the Home\nAssistant HTTP API and expect HA_URL and HA_TOKEN environment variables to be\nset. Supported domains include light, switch, fan, and media_player.\n\nif the user asks you to toggle something you will first have to get entity status and\nmake the correct change. prefer to use friendly names instead of id\n\nUse these functions when appropriate:\n- HA_GET_devices() to list devices\n- HA_GET_entity_status(entity_id_or_name) to get status\n- HA_ACTION_turn_entity_on(entity_id_or_name) to turn something on\n- HA_ACTION_turn_entity_off(entity_id_or_name) to turn something off\n- HA_ACTION_tv_remote(button_or_activity) to send remote intents or launch apps\n'

def HA_GET_devices() -> DevicesResponse | OperationResult:
    """Get list of all available Home Assistant devices and their current states.

    Example prompt: "list my home devices"

    Includes each entity's `entity_id`, `domain`, current `state`, and `friendly_name`.
    """
    return None

def HA_GET_entity_status(entity_id: str) -> EntityStatus | OperationResult:
    """Get status of a specific Home Assistant entity.

    Example prompt: "what's the status of the living room light?"

    Accepts either a full `entity_id` (e.g. 'switch.living_room_light') or a `friendly name`
    (e.g. 'Living Room Light').
    """
    return None

def HA_ACTION_turn_entity_on(entity_id: str) -> OperationResult:
    """Turn on a specific Home Assistant entity.

    Example prompt: "turn on the kitchen light"

    Accepts either a full `entity_id` (e.g. 'light.kitchen') or a `friendly name`
    (e.g. 'Kitchen Light'). Returns a clear message if the entity does not exist
    or if Home Assistant reports no changes.
    """
    return None

def HA_ACTION_turn_entity_off(entity_id: str) -> OperationResult:
    """Turn off a specific Home Assistant entity.

    Example prompt: "turn off the kitchen light"

    Accepts either a full `entity_id` (e.g. 'light.kitchen') or a `friendly name`
    (e.g. 'Kitchen Light'). Returns a clear message if the entity does not exist
    or if Home Assistant reports no changes.
    """
    return None

def HA_ACTION_tv_remote(button: str) -> str:
    """Send a TV remote action by name (single string).

    Example prompt: "open spotify on my tv"

    Examples: 'up', 'down', 'left', 'right', 'ok', 'back', 'home',
    'play', 'pause', 'stop', 'next', 'previous', 'rewind', 'fast forward',
    'mute', 'volume up', 'volume down', 'youtube', 'netflix', 'spotify', 'disney+'.

    Also accepts raw activity strings (e.g., 'https://www.youtube.com', 'com.spotify.tv.android')
    and raw command codes (e.g., 'DPAD_UP'). Uses HA_REMOTE_ENTITY_ID if set, otherwise
    defaults to 'remote.living_room_tv'.
    """
    return None

TOOLS = [HA_GET_devices, HA_GET_entity_status, HA_ACTION_turn_entity_on, HA_ACTION_turn_entity_off, HA_ACTION_tv_remote]

__all__ = ['NAME', 'SYSTEM_PROMPT', 'TOOLS', 'HA_GET_devices', 'HA_GET_entity_status', 'HA_ACTION_turn_entity_on', 'HA_ACTION_turn_entity_off', 'HA_ACTION_tv_remote']
