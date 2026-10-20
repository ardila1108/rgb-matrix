"""Weather from Open-Meteo (free, no API key): https://open-meteo.com/en/docs"""
import math

import requests

import settings

HOURS_SHOWN = 12


def _round(value):
    return int(math.floor(float(value) + 0.5))


def classify_weather(code, is_day=True):
    """Map a WMO weather code to the icon family used by the screen."""
    if code in (0, 1):
        return "clear"
    if code == 2:
        return "partly"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "cloudy"


def parse_forecast(payload):
    """Open-Meteo JSON -> {"temp", "code", "is_day", "hi", "lo", "rain": [12 percentages]}."""
    current, hourly, daily = payload["current"], payload["hourly"], payload["daily"]

    # first hourly slot at or after the current hour (times are local ISO strings)
    hour_key = current["time"][:13] + ":00"
    times = hourly["time"]
    start = next((i for i, t in enumerate(times) if t >= hour_key), len(times))
    probabilities = hourly["precipitation_probability"][start:start + HOURS_SHOWN]
    rain = [0 if p is None else _round(p) for p in probabilities]
    rain += [0] * (HOURS_SHOWN - len(rain))

    return {
        "temp": _round(current["temperature_2m"]),
        "code": int(current["weather_code"]),
        "is_day": bool(current["is_day"]),
        "hi": _round(daily["temperature_2m_max"][0]),
        "lo": _round(daily["temperature_2m_min"][0]),
        "rain": rain,
    }


def fetch_weather(get=requests.get):
    params = {
        "latitude": settings.LATITUDE,
        "longitude": settings.LONGITUDE,
        "current": "temperature_2m,weather_code,is_day",
        "hourly": "precipitation_probability",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": settings.TIMEZONE,
        "forecast_days": 2,
    }
    response = get(settings.WEATHER_API_URL, params=params, timeout=(3, 10))
    response.raise_for_status()
    return parse_forecast(response.json())
