"""Weather via Open-Meteo (free, no API key, real data).

Geocoding:  https://geocoding-api.open-meteo.com/v1/search
Forecast:   https://api.open-meteo.com/v1/forecast
"""
from __future__ import annotations

import logging

import httpx

from .errors import UpstreamError

logger = logging.getLogger("nex.weather")

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_WMO_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "light freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "rain showers",
    82: "violent rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "severe thunderstorm with hail",
}


async def get_weather(city: str) -> dict:
    """Return live weather for ``city`` using Open-Meteo."""
    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            geo = await client.get(_GEOCODE_URL, params=params)
            geo.raise_for_status()
            results = geo.json().get("results") or []
            if not results:
                raise UpstreamError(f"Could not find a place called '{city}'.")

            place = results[0]
            lat, lon = place["latitude"], place["longitude"]

            forecast_params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            }
            forecast = await client.get(_FORECAST_URL, params=forecast_params)
            forecast.raise_for_status()
            current = forecast.json().get("current", {}) or {}

            code = int(current.get("weather_code", 0))
            return {
                "city": place.get("name", city),
                "country": place.get("country", ""),
                "temperature_c": float(current.get("temperature_2m", 0.0)),
                "description": _WMO_CODES.get(code, "unknown"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_kph": current.get("wind_speed_10m"),
                "source": "open-meteo",
            }
    except UpstreamError:
        raise
    except httpx.HTTPError as exc:
        raise UpstreamError(f"Weather service unreachable: {exc}") from exc
    except (KeyError, ValueError, TypeError) as exc:
        raise UpstreamError(f"Unexpected weather response: {exc}") from exc
