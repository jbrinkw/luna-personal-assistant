# Home Assistant Extension

Control your local Home Assistant instance through natural language.

## Features

- **Device Management**: List all available devices and their states
- **Entity Control**: Turn lights, switches, fans, and media players on/off
- **Status Queries**: Check the current state of any entity
- **TV Remote Control**: Send remote commands and launch apps on Android TV devices

## Setup

### Required Environment Variables

Add these to your `.env` file in the project root:

```env
# Your Home Assistant instance URL
HA_URL=http://192.168.1.100:8123

# Long-lived access token from Home Assistant
HA_TOKEN=your_long_lived_access_token_here

# (Optional) Specify your TV remote entity ID
# Default: remote.living_room_tv
HA_REMOTE_ENTITY_ID=remote.living_room_tv
```

### Getting Your Home Assistant Token

1. Log into your Home Assistant instance
2. Click on your profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Give it a name (e.g., "Luna Integration")
6. Copy the token and add it to your `.env` file

## Usage

### Example Prompts

- "List my home devices"
- "Turn on the kitchen light"
- "Turn off the living room fan"
- "What's the status of the bedroom light?"
- "Open Spotify on my TV"
- "Press home on the remote"

### Supported Domains

This extension works with the following Home Assistant domains:
- `light` - Lights and lamps
- `switch` - Switches, outlets, and plugs
- `fan` - Fans
- `media_player` - Media players and TVs

### TV Remote Commands

The TV remote tool supports:
- **Navigation**: up, down, left, right, ok, back, home
- **Playback**: play, pause, stop, next, previous, rewind, fast forward
- **Volume**: mute, volume up, volume down
- **Apps**: youtube, netflix, spotify, disney+ (or use "open <app>")
- **Raw commands**: Any Android TV keycode (e.g., DPAD_UP, MEDIA_PLAY_PAUSE)

## Notes

- The extension uses friendly names for entities, so you can say "kitchen light" instead of "light.kitchen"
- If multiple entities match a name, the tool will ask you to be more specific
- TV remote commands target the entity specified in `HA_REMOTE_ENTITY_ID` (defaults to `remote.living_room_tv`)




