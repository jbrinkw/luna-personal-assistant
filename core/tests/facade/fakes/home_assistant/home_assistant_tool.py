"""Auto-generated fake tools for tests. DO NOT EDIT BY HAND."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


NAME = "Home Assistant"

SYSTEM_PROMPT = """
You are an assistant with tools to control a local Home Assistant instance.

Your job is to translate natural-language requests into precise tool calls
to query device status or perform actions. Typical requests include things like
turning entities on or off, checking an entity's state, or sending TV remote
intents (e.g., "open spotify on my tv"). These tools operate over the Home
Assistant HTTP API and expect HA_URL and HA_TOKEN environment variables to be
set. Supported domains include light, switch, fan, and media_player.

if the user asks you to toggle something you will first have to get entity status and
make the correct change. prefer to use friendly names instead of id

Use these functions when appropriate:
- HA_GET_devices() to list devices
- HA_GET_entity_status(entity_id_or_name) to get status
- HA_ACTION_turn_entity_on(entity_id_or_name) to turn something on
- HA_ACTION_turn_entity_off(entity_id_or_name) to turn something off
- HA_ACTION_tv_remote(button_or_activity) to send remote intents or launch apps
"""



def HA_GET_devices():
	"""Get list of all available Home Assistant devices and their current states.
Example prompt: "list my home devices"
Example Response: {"devices": [{"entity_id": "light.kitchen", "domain": "light", "state": "off", "friendly_name": "Kitchen Light"}]}
Includes each entity's `entity_id`, `domain`, current `state`, and `friendly_name`.
Example: {}
	"""
	return '{"devices": [{"entity_id": "light.kitchen", "domain": "light", "state": "off", "friendly_name": "Kitchen Light"}]}'


def HA_GET_entity_status(entity_id: 'str'):
	"""Get status of a specific Home Assistant entity.
Example prompt: "what's the status of the living room light?"
Example Response: {"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 200}}
Accepts either a full `entity_id` (e.g. 'switch.living_room_light') or a `friendly name`
(e.g. 'Living Room Light').
Example: {"entity_id": "string[entity id or friendly name]"}
	"""
	return '{"entity_id": "light.kitchen", "state": "on", "attributes": {"brightness": 200}}'


def HA_ACTION_turn_entity_on(entity_id: 'str'):
	"""Turn on a specific Home Assistant entity.
Example prompt: "turn on the kitchen light"
Example Response: {"success": true, "message": "Successfully turned on 'light.kitchen'"}
Accepts either a full `entity_id` (e.g. 'light.kitchen') or a `friendly name`
(e.g. 'Kitchen Light'). Returns a clear message if the entity does not exist
or if Home Assistant reports no changes.
Example: {"entity_id": "string[entity id or friendly name]"}
	"""
	return '{"success": true, "message": "Successfully turned on \'light.kitchen\'"}'


def HA_ACTION_turn_entity_off(entity_id: 'str'):
	"""Turn off a specific Home Assistant entity.
Example prompt: "turn off the kitchen light"
Example Response: {"success": true, "message": "Successfully turned off 'light.kitchen'"}
Accepts either a full `entity_id` (e.g. 'light.kitchen') or a `friendly name`
(e.g. 'Kitchen Light'). Returns a clear message if the entity does not exist
or if Home Assistant reports no changes.
Example: {"entity_id": "string[entity id or friendly name]"}
	"""
	return '{"success": true, "message": "Successfully turned off \'light.kitchen\'"}'


def HA_ACTION_tv_remote(button: 'str'):
	"""Send a TV remote action by name (single string).
Example prompt: "open spotify on my tv"
Example Response: {"success": true, "message": "Sent 'open spotify' to remote.living_room_tv"}
Examples: 'up', 'down', 'left', 'right', 'ok', 'back', 'home',
'play', 'pause', 'stop', 'next', 'previous', 'rewind', 'fast forward',
'mute', 'volume up', 'volume down', 'youtube', 'netflix', 'spotify', 'disney+'.

Also accepts raw activity strings (e.g., 'https://www.youtube.com', 'com.spotify.tv.android')
and raw command codes (e.g., 'DPAD_UP'). Uses HA_REMOTE_ENTITY_ID if set, otherwise
defaults to 'remote.living_room_tv'.
Example: {"button": "string[action or app name]"}
	"""
	return '{"success": true, "message": "Sent \'open spotify\' to remote.living_room_tv"}'


TOOLS = [
	HA_GET_devices,
	HA_GET_entity_status,
	HA_ACTION_turn_entity_on,
	HA_ACTION_turn_entity_off,
	HA_ACTION_tv_remote
]
