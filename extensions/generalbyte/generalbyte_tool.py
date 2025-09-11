"""GeneralByte extension — minimal utilities (notifications, basic web search).

Exposes:
- Phone notification tool via Home Assistant
- Tavily-backed web search tool
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

import requests
import json

try:  # pragma: no cover
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

try:  # pragma: no cover
    from langchain_tavily import TavilySearch  # type: ignore
except Exception:  # pragma: no cover
    TavilySearch = None  # type: ignore


# Home Assistant configuration (kept minimal; same shape as other extensions)
HA_URL = os.getenv("HA_URL", "http://192.168.0.216:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
DEFAULT_NOTIFY_SERVICE = os.getenv("DEFAULT_NOTIFY_SERVICE", "mobile_app_jeremys_iphone")

HEADERS: Dict[str, str] = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}


def _call_service(domain: str, service: str, data: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{HA_URL}/api/services/{domain}/{service}"
    response = requests.post(url, headers=HEADERS, json=data, timeout=10)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {}
class OperationResult(BaseModel):
    success: bool
    message: str



class WebSearchResult(BaseModel):
    title: str
    url: str
    content: str


class WebSearchResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    results: List[WebSearchResult] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)


class WeatherCurrent(BaseModel):
    time: Optional[str] = None
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    weather_code: Optional[int] = None
    weather_description: Optional[str] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None


class WeatherResponse(BaseModel):
    location_query: str
    resolved_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    current: Optional[WeatherCurrent] = None


def _wmo_code_to_description(code: int) -> str:
    mapping: Dict[int, str] = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(int(code), "Unknown")


def _geocode_open_meteo(name: str) -> Optional[Dict[str, Any]]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": name, "count": 1, "language": "en", "format": "json"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = data.get("results") or []
        if not results:
            # Minimal normalization attempts for common US state abbreviations
            normalized_candidates = []
            # Example: "Charlotte, NC" -> try "Charlotte, North Carolina" then "Charlotte"
            if ", NC" in name:
                normalized_candidates.append(name.replace(", NC", ", North Carolina"))
                normalized_candidates.append(name.replace(", NC", ""))
            elif name.strip().lower() == "charlotte":
                normalized_candidates.append("Charlotte, North Carolina")
            elif name.strip().lower() == "charlotte, nc":
                normalized_candidates.append("Charlotte, North Carolina")
                normalized_candidates.append("Charlotte")

            for candidate in normalized_candidates:
                try:
                    r2 = requests.get(url, params={**params, "name": candidate}, timeout=10)
                    r2.raise_for_status()
                    data2 = r2.json()
                    results2 = data2.get("results") or []
                    if results2:
                        r0 = results2[0]
                        return {
                            "name": r0.get("name"),
                            "latitude": r0.get("latitude"),
                            "longitude": r0.get("longitude"),
                            "country": r0.get("country"),
                            "admin1": r0.get("admin1"),
                        }
                except Exception:
                    continue
            return None
        r0 = results[0]
        return {
            "name": r0.get("name"),
            "latitude": r0.get("latitude"),
            "longitude": r0.get("longitude"),
            "country": r0.get("country"),
            "admin1": r0.get("admin1"),
        }
    except Exception:
        return None


# Ensure forward refs are resolved under postponed annotations
OperationResult.model_rebuild()
WebSearchResult.model_rebuild()
WebSearchResponse.model_rebuild()
WeatherCurrent.model_rebuild()
WeatherResponse.model_rebuild()


NAME = "GeneralByte"

SYSTEM_PROMPT = """
General utilities for the personal assistant, focusing on notifications and basic web search.

Use these tools to:
- Send phone notifications via Home Assistant's notify service (requires HA_URL and HA_TOKEN).
- Perform general web searches using Tavily (requires TAVILY_API_KEY).
- Get current weather (defaults to Charlotte, NC; pass a location to override).
"""


def GENERAL_ACTION_send_phone_notification(message: str, title: str = "Notification", service: Optional[str] = None) -> OperationResult:
    """Send a phone notification via Home Assistant.
    Example Prompt: Notify me: "Garage door is open".
    Example Response: {"success": true, "message": "Notification sent"}
    Example Args: {"message": "string[notification text]", "title": "string[optional title]", "service": "string[optional notify service]"}
    Uses the configured notify service (or provided service) to deliver a push notification.
    """
    if not HA_TOKEN:
        return OperationResult(success=False, message="Home Assistant token not configured")
    target_service = service or DEFAULT_NOTIFY_SERVICE
    _call_service("notify", target_service, {"title": title, "message": message})
    return OperationResult(success=True, message="Notification sent")


def GENERAL_GET_web_search(query: str, max_results: int = 5) -> WebSearchResponse | OperationResult:
    """Search the web and return top results (title, URL, snippet).
    Example Prompt: "search for langchain tavily integration"
    Example Response: {"query": "...", "answer": null, "results": [{"title": "...", "url": "...", "content": "..."}], "images": []}
    Example Args: {"query": "string[search terms]", "max_results": int[number of results]}
    """
    if TavilySearch is None:
        return OperationResult(
            success=False,
            message=(
                "Tavily tool not available. Install it with 'pip install -U langchain-tavily'."
            ),
        )
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or not api_key.strip():
        return OperationResult(success=False, message="TAVILY_API_KEY is not configured")

    try:
        tool = TavilySearch(
            max_results=max_results,
            topic="general",
            # Keep responses compact to fit context nicely
            include_answer=False,
            include_raw_content=False,
            include_images=False,
            include_image_descriptions=False,
            search_depth="basic",
        )
        raw = tool.invoke({"query": query})
        # Normalize output whether dict or ToolMessage with JSON string content
        if isinstance(raw, dict):
            data = raw
        else:
            content = getattr(raw, "content", raw)
            if isinstance(content, (bytes, bytearray)):
                content = content.decode("utf-8", "ignore")
            try:
                data = json.loads(content) if isinstance(content, str) else {}
            except Exception:
                data = {}

        items = []
        for r in (data.get("results") or []):
            try:
                title = str(r.get("title") or "")
                url = str(r.get("url") or "")
                # Prefer concise cleaned snippet
                content = str(r.get("content") or r.get("raw_content") or "")
                items.append(WebSearchResult(title=title, url=url, content=content))
            except Exception:
                continue

        images = []
        try:
            images = [str(i) for i in (data.get("images") or []) if isinstance(i, str)]
        except Exception:
            images = []

        return WebSearchResponse(
            query=query,
            answer=(data.get("answer") if isinstance(data.get("answer"), str) else None),
            results=items,
            images=images,
        )
    except Exception as e:  # pragma: no cover
        return OperationResult(success=False, message=f"Search error: {str(e)}")


def GENERAL_GET_weather(location: Optional[str] = None) -> WeatherResponse | OperationResult:
    """Get current weather for a location.
    Example Prompt: "weather in Paris" (or call without arguments for Charlotte)
    Example Response: {"location_query": "Paris", "resolved_name": "Paris, Île-de-France, France", "current": {"temperature_c": 21.5, "weather_description": "Clear sky"}}
    Example Args: {"location": "string[city, state/country]"}
    Defaults to Charlotte, NC if no location is provided.
    """
    place = (location or "").strip() or "Charlotte, NC"
    geo = _geocode_open_meteo(place)
    if not geo:
        return OperationResult(success=False, message=f"Could not resolve location: {place}")

    latitude = geo.get("latitude")
    longitude = geo.get("longitude")
    if latitude is None or longitude is None:
        return OperationResult(success=False, message="Geocoding did not return coordinates")

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m",
            "timezone": "auto",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current") or {}
        code_raw = current.get("weather_code")
        description = _wmo_code_to_description(int(code_raw)) if isinstance(code_raw, (int, float)) else None

        current_model = WeatherCurrent(
            time=str(current.get("time")) if current.get("time") is not None else None,
            temperature_c=float(current.get("temperature_2m")) if current.get("temperature_2m") is not None else None,
            apparent_temperature_c=float(current.get("apparent_temperature")) if current.get("apparent_temperature") is not None else None,
            weather_code=int(code_raw) if isinstance(code_raw, (int, float)) else None,
            weather_description=description,
            wind_speed_kmh=float(current.get("wind_speed_10m")) if current.get("wind_speed_10m") is not None else None,
            wind_direction_deg=float(current.get("wind_direction_10m")) if current.get("wind_direction_10m") is not None else None,
        )

        resolved_name_parts = [p for p in [geo.get("name"), geo.get("admin1"), geo.get("country")] if p]
        resolved_name = ", ".join(resolved_name_parts) if resolved_name_parts else None

        return WeatherResponse(
            location_query=place,
            resolved_name=resolved_name,
            latitude=float(latitude) if latitude is not None else None,
            longitude=float(longitude) if longitude is not None else None,
            timezone=str(data.get("timezone")) if data.get("timezone") is not None else None,
            current=current_model,
        )
    except Exception as e:  # pragma: no cover
        return OperationResult(success=False, message=f"Weather error: {str(e)}")


TOOLS = [
    GENERAL_ACTION_send_phone_notification,
    GENERAL_GET_web_search,
    GENERAL_GET_weather,
]


