"""Auto-generated fake tools for tests. DO NOT EDIT BY HAND."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


NAME = "GeneralByte"

SYSTEM_PROMPT = """
General utilities for the personal assistant, focusing on notifications and basic web search.

Use these tools to:
- Send phone notifications via Home Assistant's notify service (requires HA_URL and HA_TOKEN).
- Perform general web searches using Tavily (requires TAVILY_API_KEY).
- Get current weather (defaults to Charlotte, NC; pass a location to override).
"""



def GENERAL_ACTION_send_phone_notification(message: 'str', title: 'str' = 'Notification', service: 'Optional[str]' = None):
	"""Send a phone notification via Home Assistant.
Notify me: "Garage door is open".
Example Response: {"success": true, "message": "Notification sent"}
Uses the configured notify service (or provided service) to deliver a push notification.
Example: {"message": "string[notification text]", "title": "string[optional title]", "service": "string[optional notify service]"}
	"""
	return '{"success": true, "message": "Notification sent"}'


def GENERAL_GET_web_search(query: 'str', max_results: 'int' = 5):
	"""Search the web via Tavily and return top results (title, URL, snippet).
Example: "search for langchain tavily integration"
Example Response: {"query": "...", "answer": null, "results": [{"title": "...", "url": "...", "content": "..."}], "images": []}
Example: {"query": "string[search terms]", "max_results": int[number of results]}
	"""
	return '{"query": "...", "answer": null, "results": [{"title": "...", "url": "...", "content": "..."}], "images": []}'


def GENERAL_GET_weather(location: 'Optional[str]' = None):
	"""Get current weather for a location.
Example: "weather in Paris" or just call without arguments for Charlotte.
Example Response: {"location_query": "Paris", "resolved_name": "Paris, Île-de-France, France", "current": {"temperature_c": 21.5, "weather_description": "Clear sky"}}
Defaults to Charlotte, NC if no location is provided.
Example: {"location": "string[city, state/country]"}
	"""
	return '{"location_query": "Paris", "resolved_name": "Paris, Île-de-France, France", "current": {"temperature_c": 21.5, "weather_description": "Clear sky"}}'


TOOLS = [
	GENERAL_ACTION_send_phone_notification,
	GENERAL_GET_web_search,
	GENERAL_GET_weather
]
