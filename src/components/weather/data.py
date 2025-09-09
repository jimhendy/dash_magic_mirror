import datetime
from typing import Any

import httpx
from loguru import logger

from utils.file_cache import cache_json

from .constants import BASE_URL, FORECAST_DAYS, HOURLY_WINDOW_DAYS, HTTP_TIMEOUT


@cache_json(valid_lifetime=datetime.timedelta(minutes=15))
def fetch_weather_data(api_key: str, postcode: str) -> dict[str, Any]:
    """Fetch weather data from WeatherAPI.com."""
    try:
        # Get current weather and multi-day forecast in one call
        forecast_url = f"{BASE_URL}/forecast.json"
        params = {
            "key": api_key,
            "q": postcode,
            "days": FORECAST_DAYS,
            "aqi": "no",
            "alerts": "no",
        }

        response = httpx.get(forecast_url, params=params, timeout=HTTP_TIMEOUT)
        response.raise_for_status()

        return response.json()

    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to fetch weather data: {e}")
        return {}


def _icon_url(icon: str) -> str:
    """Construct the full URL for the weather icon."""
    if icon.startswith("//"):
        icon = "https:" + icon
    return icon


def _extract_day_details(day_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract API details from the day's forecast."""
    details = {
        "high": round(day_dict.get("maxtemp_c", 0)),
        "low": round(day_dict.get("mintemp_c", 0)),
        "description": day_dict.get("condition", {}).get("text", "Unknown"),
        "rain_chance": day_dict.get("daily_chance_of_rain", 0),
        "icon": _icon_url(day_dict.get("condition", {}).get("icon", "")),
    }
    return details


def _extract_current_details(current_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract API details from the current weather."""
    details = {
        "temperature": round(current_dict.get("temp_c", 0)),
        "condition": current_dict.get("condition", {}).get("text", "Unknown"),
        "icon": _icon_url(
            current_dict.get("condition", {}).get("icon", ""),
        ),
    }
    return details


def process_weather_data(raw_data: dict[str, Any], postcode: str) -> dict[str, Any]:
    """Process raw WeatherAPI data into our format."""
    forecast_days = raw_data.get("forecast", {}).get("forecastday", [])
    return {
        "current": _extract_current_details(raw_data.get("current", {})),
        "today": _extract_day_details(forecast_days[0].get("day", {})),
        "tomorrow": _extract_day_details(forecast_days[1].get("day", {})),
        "location": raw_data.get("location", {}).get("name", postcode),
    }


def _extract_hourly_details(hour_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract details for a single hour from the forecast."""
    return {
        "time": hour_dict.get("time", ""),
        "temp_c": round(hour_dict.get("temp_c", 0)),
        "condition": hour_dict.get("condition", {}).get("text", "Unknown"),
        "icon": _icon_url(hour_dict.get("condition", {}).get("icon", "")),
        "rain_chance": hour_dict.get("chance_of_rain", 0),
        "wind_mph": round(hour_dict.get("wind_mph", 0)),
        "wind_dir": hour_dict.get("wind_dir", ""),
        "humidity": hour_dict.get("humidity", 0),
        "feels_like": round(hour_dict.get("feelslike_c", 0)),
        "is_day": hour_dict.get("is_day", 0),
        "cloud": hour_dict.get("cloud", 0),
    }


def _datetime_from_time_str(time_str: str, date: datetime.date) -> datetime.datetime:
    """Convert a time string (08:02 PM) to a datetime on the supplied date."""
    time_parts = time_str.split(" ")
    if len(time_parts) != 2:
        return datetime.datetime.combine(date, datetime.time.min)

    hour_minute = time_parts[0].split(":")
    if len(hour_minute) != 2:
        return datetime.datetime.combine(date, datetime.time.min)

    hour = int(hour_minute[0]) if hour_minute[0].isdigit() else 0
    minute = int(hour_minute[1]) if hour_minute[1].isdigit() else 0

    if time_parts[1].upper() == "PM" and hour < 12:
        hour += 12
    elif time_parts[1].upper() == "AM" and hour == 12:
        hour = 0

    return datetime.datetime.combine(date, datetime.time(hour, minute))


def _extract_daily_details(day_data: dict[str, Any]) -> dict[str, Any]:
    """Extract detailed daily forecast data."""
    day = day_data.get("day", {})
    astro = day_data.get("astro", {})

    date = datetime.datetime.fromisoformat(day_data.get("date", "")).date()

    return {
        "date": date,
        "high": round(day.get("maxtemp_c", 0)),
        "low": round(day.get("mintemp_c", 0)),
        "condition": day.get("condition", {}).get("text", "Unknown"),
        "icon": _icon_url(day.get("condition", {}).get("icon", "")),
        "rain_chance": day.get("daily_chance_of_rain", 0),
        "total_precip": day.get("totalprecip_mm", 0),
        "max_wind": round(day.get("maxwind_mph", 0)),
        "avg_humidity": day.get("avghumidity", 0),
        "uv_index": day.get("uv", 0),
        "sunrise": _datetime_from_time_str(astro.get("sunrise", ""), date),
        "sunset": _datetime_from_time_str(astro.get("sunset", ""), date),
        "moon_phase": astro.get("moon_phase", ""),
    }


def process_detailed_weather_data(
    raw_data: dict[str, Any],
    postcode: str,
) -> dict[str, Any]:
    """Process weather data for detailed/full-screen view."""
    forecast_days = raw_data.get("forecast", {}).get("forecastday", [])

    # Get next 24 hours of hourly data
    hourly_data = []
    for day in forecast_days[:HOURLY_WINDOW_DAYS]:  # Today and tomorrow
        hours = day.get("hour", [])
        for hour in hours:
            hourly_data.append(_extract_hourly_details(hour))

    # Get daily forecasts for next N days
    daily_data = []
    for day_data in forecast_days:
        daily_data.append(_extract_daily_details(day_data))

    return {
        "current": _extract_current_details(raw_data.get("current", {})),
        "location": raw_data.get("location", {}).get("name", postcode),
        "hourly": hourly_data,
        "daily": daily_data,
    }
