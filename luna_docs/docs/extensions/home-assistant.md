# Home Assistant — User Guide

## Purpose
Control a local Home Assistant instance: list devices, get entity status, toggle entities, and send TV remote intents.

## Prerequisites
- Environment: `HA_URL`, `HA_TOKEN` must be set.
- Supported domains: `light`, `switch`, `fan`, `media_player`.

## Tools

### `HA_GET_devices`
- Summary: Get list of all available Home Assistant devices and their current states.
- Example Prompt: list my home devices
- Example Args: {}
- Returns: {"devices": [{"entity_id", "domain", "state", "friendly_name"}]}.

### `HA_GET_entity_status`
- Summary: Get status of a specific Home Assistant entity.
- Example Prompt: what's the status of the living room light?
- Example Args: {"entity_id": "string[entity id or friendly name]"}
- Returns: {"entity_id", "state", "attributes"}.

### `HA_ACTION_turn_entity_on`
- Summary: Turn on a specific Home Assistant entity.
- Example Prompt: turn on the kitchen light
- Example Args: {"entity_id": "string[entity id or friendly name]"}
- Returns: {"success": bool, "message": string}.

### `HA_ACTION_turn_entity_off`
- Summary: Turn off a specific Home Assistant entity.
- Example Prompt: turn off the kitchen light
- Example Args: {"entity_id": "string[entity id or friendly name]"}
- Returns: {"success": bool, "message": string}.

### `HA_ACTION_tv_remote`
- Summary: Send a TV remote action by name (or raw activity/command).
- Example Prompt: open spotify on my tv
- Example Args: {"button": "string[action/app]"}
- Returns: {"success": bool, "message": string}.
- Notes: Uses `HA_REMOTE_ENTITY_ID` if set, else defaults to `remote.living_room_tv`.
