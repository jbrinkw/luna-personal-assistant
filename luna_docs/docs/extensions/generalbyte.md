# GeneralByte — User Guide

## Purpose
General utilities for notifications, web search, and current weather.

## Tools

### `GENERAL_ACTION_send_phone_notification`
- Summary: Send a phone notification via Home Assistant.
- Example Prompt: Notify me: "Garage door is open".
- Example Args: {"message": "string", "title": "string(optional)", "service": "string(optional)"}
- Returns: {"success": bool, "message": string}.
- Notes: Requires `HA_URL` and `HA_TOKEN` env vars; uses `DEFAULT_NOTIFY_SERVICE` if not provided.

### `GENERAL_GET_web_search`
- Summary: Search the web and return top results (title, URL, snippet).
- Example Prompt: search for langchain tavily integration
- Example Args: {"query": "string", "max_results": int}
- Returns: {"query": string, "answer": string|null, "results": [{"title", "url", "content"}], "images": []}.
- Notes: Requires `TAVILY_API_KEY`. Install `langchain-tavily`.

### `GENERAL_GET_weather`
- Summary: Get current weather for a location.
- Example Prompt: weather in Paris
- Example Args: {"location": "string[city, state/country]"}
- Returns: structured weather with resolved name and current conditions.
- Notes: Defaults to Charlotte, NC when no location provided.
