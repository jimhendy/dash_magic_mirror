from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload
from utils.styles import COLORS

from .data import (
    async_fetch_weather_data,
    process_detailed_weather_data,
    process_weather_data,
)
from .full_screen import render_weather_fullscreen
from .summary import render_weather_summary


class Weather(DataDrivenComponent):
    """Current conditions, the next few hours, and a 3-day forecast for a UK
    postcode.

    Uses WeatherAPI.com for weather data.
    Requires a free API key from https://www.weatherapi.com/signup.aspx
    """

    title = "Weather"
    icon = "mdi:weather-partly-cloudy"
    accent = COLORS["gold"]
    refresh_seconds = 15 * 60
    jitter_seconds = 60
    placeholder_error = "Weather unavailable"
    placeholder_loading = "Loading weather…"

    def __init__(self, postcode: str, api_key: str, **kwargs):
        self.postcode = postcode.upper().replace(" ", "")
        self.api_key = api_key

        if not self.api_key:
            msg = "Please set the WEATHER_API_KEY environment variable with your WeatherAPI.com key."
            raise ValueError(msg)

        super().__init__(name="weather", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        raw = await async_fetch_weather_data(self.api_key, self.postcode)
        if not raw:
            logger.warning(f"Weather API returned no data for {self.postcode}")
            return None

        try:
            summary_data = process_weather_data(raw, self.postcode)
            detailed_data = process_detailed_weather_data(raw, self.postcode)
            hourly = detailed_data.get("hourly", [])
            summary = render_weather_summary(
                summary_data, hourly, detailed_data.get("daily", [])
            )
            detail = render_weather_fullscreen(detailed_data)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering weather payload")
            return None

        current = summary_data.get("current", {})
        return ComponentPayload(
            summary=summary,
            detail=detail,
            subtitle=f"{summary_data.get('location', '')} · {current.get('condition', '')}",
            raw={"summary": summary_data, "detailed": detailed_data},
        )
