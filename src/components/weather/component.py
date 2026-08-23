from dash import html
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
    """Weather component for the Magic Mirror application.
    Displays current weather, chance of rain, and 3-day forecast for a given UK postcode.

    Uses WeatherAPI.com for weather data.
    Requires a free API key from https://www.weatherapi.com/signup.aspx
    """

    icon_size = "5.5rem"
    refresh_seconds = 15 * 60
    jitter_seconds = 60
    placeholder_error = "Weather unavailable"
    placeholder_loading = "Loading weather..."

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
            return ComponentPayload(
                summary=self._build_placeholder(self.placeholder_error),
            )

        try:
            summary_data = process_weather_data(raw, self.postcode)
            detailed_data = process_detailed_weather_data(raw, self.postcode)
            summary_children = render_weather_summary(
                summary_data,
                self.component_id,
                self.icon_size,
            )
            content = render_weather_fullscreen(detailed_data, self.component_id)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering weather payload")
            return ComponentPayload(
                summary=self._build_placeholder(self.placeholder_error),
            )

        title_text = summary_data.get("current", {}).get("condition", "Weather")
        title = html.Div(
            title_text,
            className="text-m",
            **{"data-component-name": self.name},
        )

        return ComponentPayload(
            summary=summary_children,
            fullscreen_title=title,
            fullscreen_content=content,
            raw={
                "summary": summary_data,
                "detailed": detailed_data,
            },
        )

    def _content_style(self) -> dict:
        return {"color": COLORS["text"], "textAlign": "center"}
