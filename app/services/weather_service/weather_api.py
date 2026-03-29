"""
app/services/weather_service/weather_api.py
Live weather service using WeatherAPI.com (https://www.weatherapi.com/).
Requires WEATHER_API_KEY in .env — free tier (1M calls/month) is sufficient.
"""

import requests
from typing import Dict, Any, Tuple
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger("weather_service")

_BASE_URL = "http://api.weatherapi.com/v1/current.json"


def _severity_from_response(data: Dict[str, Any]) -> Tuple[float, bool]:
    """
    Derive a 0-1 severity score and alert flag from a WeatherAPI current response.
    WeatherAPI condition codes: https://www.weatherapi.com/docs/weather_conditions.json
    """
    current   = data.get("current", {})
    condition = current.get("condition", {})
    code      = condition.get("code", 1000)
    wind_kph  = current.get("wind_kph", 0)
    precip_mm = current.get("precip_mm", 0)
    vis_km    = current.get("vis_km", 10)

    severity = 0.10

    if code in (1087, 1273, 1276, 1279, 1282):
        severity = 0.85
    elif code in (1192, 1195, 1201, 1243, 1246):
        severity = 0.75
    elif code in (1063, 1150, 1153, 1180, 1183, 1186, 1189, 1240):
        severity = 0.45
    elif code in (1072, 1168, 1171):
        severity = 0.30
    elif code in (1114, 1117, 1222, 1225, 1237, 1255, 1258, 1261, 1264):
        severity = 0.70
    elif code in (1066, 1069, 1204, 1207, 1210, 1213, 1216, 1219):
        severity = 0.45
    elif code in (1030, 1135, 1147):
        severity = 0.40
    elif code in (1006, 1009):
        severity = 0.15
    else:
        severity = 0.10

    if wind_kph > 70:
        severity = min(1.0, severity + 0.20)
    elif wind_kph > 40:
        severity = min(1.0, severity + 0.10)

    if precip_mm > 20:
        severity = min(1.0, severity + 0.15)
    elif precip_mm > 8:
        severity = min(1.0, severity + 0.08)

    if vis_km < 1:
        severity = min(1.0, severity + 0.15)
    elif vis_km < 3:
        severity = min(1.0, severity + 0.07)

    alert_active = severity >= 0.35 or wind_kph > 40 or precip_mm > 5
    return round(severity, 3), alert_active


def _fetch_city(city: str, api_key: str) -> Dict[str, Any]:
    """Fetch current weather for a single city from WeatherAPI.com."""
    try:
        resp = requests.get(
            _BASE_URL,
            params={"key": api_key, "q": city, "aqi": "no"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()

        current   = data["current"]
        condition = current["condition"]
        severity, alert_active = _severity_from_response(data)

        return {
            "location":     city,
            "condition":    condition["text"],
            "severity":     severity,
            "alert_active": alert_active,
            "wind_kph":     current.get("wind_kph", 0),
            "precip_mm":    current.get("precip_mm", 0),
            "vis_km":       current.get("vis_km", 10),
            "temp_c":       current.get("temp_c"),
            "humidity":     current.get("humidity"),
        }

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        logger.warning(f"WeatherAPI HTTP {status} for '{city}': {e}")
        raise
    except requests.exceptions.Timeout:
        logger.warning(f"WeatherAPI timeout for '{city}'")
        raise
    except Exception as e:
        logger.error(f"WeatherAPI fetch failed for '{city}': {e}")
        raise


def get_weather_data(origin: str, destination: str) -> Dict[str, Any]:
    """
    Fetch live weather from WeatherAPI.com for the origin -> destination corridor.

    Returns a dict with:
        - origin_weather:       weather profile at origin
        - destination_weather:  weather profile at destination
        - corridor_severity:    combined severity score (0-1)
        - active_alerts:        list of alert descriptions
        - risk_score:           normalised weather risk (0-100)
    """
    settings = get_settings()
    api_key  = settings.weather_api_key

    _FALLBACK = {
        "severity": 0.30, "condition": "Unknown", "alert_active": False,
        "location": "", "wind_kph": 0, "precip_mm": 0, "vis_km": 10,
    }

    try:
        origin_wx = _fetch_city(origin, api_key)
    except Exception as e:
        logger.error(f"Origin weather unavailable, using fallback: {e}")
        origin_wx = {**_FALLBACK, "location": origin}

    try:
        dest_wx = _fetch_city(destination, api_key)
    except Exception as e:
        logger.error(f"Destination weather unavailable, using fallback: {e}")
        dest_wx = {**_FALLBACK, "location": destination}

    corridor_severity = round(
        (origin_wx["severity"] * 0.6) + (dest_wx["severity"] * 0.4), 3
    )

    alerts = []
    if origin_wx["alert_active"]:
        alerts.append(f"{origin}: {origin_wx['condition']} (severity {origin_wx['severity']:.0%})")
    if dest_wx["alert_active"]:
        alerts.append(f"{destination}: {dest_wx['condition']} (severity {dest_wx['severity']:.0%})")

    risk_score = round(corridor_severity * 100, 1)

    result = {
        "origin_weather":      origin_wx,
        "destination_weather": dest_wx,
        "corridor_severity":   corridor_severity,
        "active_alerts":       alerts,
        "risk_score":          risk_score,
    }

    logger.info(
        f"Weather fetched (WeatherAPI.com) | {origin}->{destination} "
        f"| corridor_severity={corridor_severity:.2f} | risk={risk_score}"
    )
    return result
