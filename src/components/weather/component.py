from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent, PreloadedFullScreenMixin

from .data import (
    fetch_weather_data,
    process_detailed_weather_data,
    process_weather_data,
)
from .full_screen import render_weather_fullscreen
from .summary import render_weather_summary


class Weather(PreloadedFullScreenMixin, BaseComponent):
    """Weather component for the Magic Mirror application.
    Displays current weather, chance of rain, and 3-day forecast for a given UK postcode.

    Uses WeatherAPI.com for weather data.
    Requires a free API key from https://www.weatherapi.com/signup.aspx
    """

    icon_size = "7rem"

    def __init__(self, postcode: str, api_key: str, **kwargs):
        # Disable preloaded_full_screen because Dash components cannot be placed inside dcc.Store
        super().__init__(name="weather", preloaded_full_screen=False, **kwargs)
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
                *self.preload_fullscreen_stores(),
                html.Div(
                    id=f"{self.component_id}-content",
                    style={
                        "color": "#FFFFFF",
                        "fontSize": "14px",
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

        @app.callback(
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval", "n_intervals"),
            prevent_initial_call=False,
        )
        def populate_weather_fullscreen(_n):
            try:
                api_data = fetch_weather_data(self.api_key, self.postcode)
                weather_data = process_detailed_weather_data(api_data, self.postcode)
                content = render_weather_fullscreen(weather_data, self.component_id)
                title = html.Div(
                    weather_data["current"]["condition"],
                    className="text-m",
                    **{"data-component-name": self.name},
                )
                return title, content
            except Exception as e:
                logger.error(f"Error preparing weather full screen: {e}")
                return None, None
