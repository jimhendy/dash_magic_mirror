from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.models import FullScreenResult
from utils.styles import FONT_FAMILY

from .data import (
    fetch_weather_data,
    process_detailed_weather_data,
    process_weather_data,
)
from .full_screen import render_weather_fullscreen
from .summary import render_weather_summary


class Weather(BaseComponent):
    """Weather component for the Magic Mirror application.
    Displays current weather, chance of rain, and 3-day forecast for a given UK postcode.

    Uses WeatherAPI.com for weather data.
    Requires a free API key from https://www.weatherapi.com/signup.aspx
    """

    icon_size = "7rem"

    def __init__(self, postcode: str, api_key: str, **kwargs):
        super().__init__(name="weather", **kwargs)
        self.postcode = postcode.upper().replace(" ", "")
        self.api_key = api_key

        if not self.api_key:
            msg = "Please set the WEATHER_API_KEY environment variable with your WeatherAPI.com key."
            raise ValueError(msg)

    def _summary_layout(self):
        """Returns the layout of the Weather component."""
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=15 * 60 * 1000,  # Update every 15 minutes
                    n_intervals=0,
                ),
                html.Div(
                    id=f"{self.component_id}-content",
                    style={
                        "color": "#FFFFFF",
                        "fontSize": "14px",
                        "fontFamily": FONT_FAMILY,
                        "textAlign": "center",
                    },
                ),
            ],
        )

    def _add_callbacks(self, app):
        """Add callbacks for the Weather component."""

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Input(f"{self.component_id}-interval", "n_intervals"),
        )
        def update_weather(_):
            try:
                api_data = fetch_weather_data(self.api_key, self.postcode)
                weather_data = process_weather_data(api_data, self.postcode)
                return render_weather_summary(
                    weather_data,
                    self.component_id,
                    self.icon_size,
                )
            except Exception as e:
                logger.error(f"Error updating weather: {e}")
                return html.Div("Weather unavailable", style={"color": "#FF6B6B"})

    def full_screen_content(self) -> FullScreenResult:
        """Returns the full-screen layout of the Weather component."""
        try:
            api_data = fetch_weather_data(self.api_key, self.postcode)
            weather_data = process_detailed_weather_data(api_data, self.postcode)
            content = render_weather_fullscreen(weather_data, self.component_id)
            title = weather_data["current"]["condition"]
            return FullScreenResult(content=content, title=title)
        except Exception as e:
            logger.error(f"Error loading full-screen weather: {e}")
            return FullScreenResult(
                content=html.Div(
                    "Weather unavailable",
                    style={
                        "color": "#FF6B6B",
                        "textAlign": "center",
                        "padding": "2rem",
                        "fontSize": "1.5rem",
                    },
                ),
                title="Weather unavailable",
            )
