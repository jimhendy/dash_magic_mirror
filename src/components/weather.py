import datetime

import dash_mantine_components as dmc
import httpx
from dash import Input, Output, dcc, html
from dash_iconify import DashIconify
from loguru import logger

from components.base import BaseComponent
from utils.file_cache import cache_json


class Weather(BaseComponent):
    """Weather component for the Magic Mirror application.
    Displays current weather, chance of rain, and 3-day forecast for a given UK postcode.

    Uses WeatherAPI.com for weather data.
    Requires a free API key from https://www.weatherapi.com/signup.aspx
    """

    icon_size = "7rem"

    def __init__(self, postcode: str, api_key: str, *args, **kwargs):
        super().__init__(name="weather", *args, **kwargs)
        self.postcode = postcode.upper().replace(" ", "")
        self.api_key = api_key
        self.base_url = "http://api.weatherapi.com/v1"

        if not self.api_key:
            msg = "Please set the WEATHER_API_KEY environment variable with your WeatherAPI.com key."
            raise ValueError(msg)

    def layout(self):
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
                        "fontFamily": "'Inter', 'Roboto', 'Segoe UI', 'Helvetica Neue', sans-serif",
                        "textAlign": "center",
                    },
                ),
            ],
        )

    def add_callbacks(self, app):
        """Add callbacks for the Weather component."""

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Input(f"{self.component_id}-interval", "n_intervals"),
        )
        def update_weather(_):
            try:
                api_data = self.fetch()
                weather_data = self._process_weather_data(api_data)
                return self._render_weather(weather_data)
            except Exception as e:
                logger.error(f"Error updating weather: {e}")
                return html.Div("Weather unavailable", style={"color": "#FF6B6B"})

    @cache_json(valid_lifetime=datetime.timedelta(minutes=15))
    def fetch(self) -> dict:
        """Fetch weather data from WeatherAPI.com."""
        try:
            # Get current weather and 3-day forecast in one call
            forecast_url = f"{self.base_url}/forecast.json"
            params = {
                "key": self.api_key,
                "q": self.postcode,
                "days": 3,
                "aqi": "no",
                "alerts": "no",
            }

            response = httpx.get(forecast_url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return {}

    @staticmethod
    def _icon_url(icon: str) -> str:
        """Construct the full URL for the weather icon."""
        if icon.startswith("//"):
            icon = "https:" + icon
        return icon

    @staticmethod
    def _extract_day_details(day_dict: dict) -> dict:
        """Extract API details from the day's forecast."""
        details = {
            "high": round(day_dict.get("maxtemp_c", 0)),
            "low": round(day_dict.get("mintemp_c", 0)),
            "description": day_dict.get("condition", {}).get("text", "Unknown"),
            "rain_chance": day_dict.get("daily_chance_of_rain", 0),
            "icon": Weather._icon_url(day_dict.get("condition", {}).get("icon", "")),
        }
        return details

    @staticmethod
    def _extract_current_details(current_dict: dict) -> dict:
        """Extract API details from the current weather."""
        details = {
            "temperature": round(current_dict.get("temp_c", 0)),
            "condition": current_dict.get("condition", {}).get("text", "Unknown"),
            "icon": Weather._icon_url(
                current_dict.get("condition", {}).get("icon", ""),
            ),
        }
        return details

    def _process_weather_data(self, raw_data: dict) -> dict:
        """Process raw WeatherAPI data into our format."""
        forecast_days = raw_data.get("forecast", {}).get("forecastday", [])
        return {
            "current": self._extract_current_details(raw_data.get("current", {})),
            "today": self._extract_day_details(forecast_days[0].get("day", {})),
            "tomorrow": self._extract_day_details(forecast_days[1].get("day", {})),
            "location": raw_data.get("location", {}).get("name", self.postcode),
        }

    @staticmethod
    def _high_low_rain(day_data: dict) -> html.Div:
        high = day_data.get("high", "?")
        low = day_data.get("low", "?")
        rain = day_data.get("rain_chance", "?")

        return html.Div(
            style={"display": "flex", "justifyContent": "space-between"},
            className="text-ms",
            children=[
                html.Div(
                    [
                        DashIconify(
                            icon="mdi:arrow-up",
                            color="red",
                            style={"marginRight": "0.5rem"},
                        ),
                        html.Div(high),
                        html.Div("°C", className="degrees"),
                    ],
                    className="centered-content",
                ),
                html.Div(
                    [
                        DashIconify(
                            icon="mdi:arrow-down",
                            color="#5f9fff",
                            style={"marginRight": "0.5rem"},
                        ),
                        html.Div(low),
                        html.Div("°C", className="degrees"),
                    ],
                    className="centered-content",
                ),
                html.Div(
                    [
                        DashIconify(
                            icon="mdi:weather-rainy",
                            color="white",
                            style={"marginRight": "0.5rem"},
                        ),
                        html.Div(rain),
                        html.Div("%", className="degrees"),
                    ],
                    className="centered-content",
                ),
            ],
        )

    @staticmethod
    def _tomorrow_day() -> str:
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        return tomorrow.strftime("%a")

    def _render_weather(self, weather_data: dict) -> html.Div:
        """Render the weather component in Today/Tomorrow format."""
        current = weather_data.get("current", {})
        today = weather_data.get("today", {})
        tomorrow = weather_data.get("tomorrow", {})

        return html.Div(
            [
                html.Div(
                    id=f"{self.component_id}-current-weather",
                    style={"width": "48%"},
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    id=f"{self.component_id}-current-temperature",
                                    children=[
                                        html.Div(
                                            current.get("temperature", "?"),
                                            className="text-l",
                                        ),
                                        html.Div("°C", className="text-m degrees"),
                                    ],
                                    style={"display": "flex", "alignItems": "baseline"},
                                ),
                                dmc.Image(
                                    src=current.get("icon", ""),
                                    w=self.icon_size,
                                    h=self.icon_size,
                                ),
                            ],
                            className="centered-content gap-m",
                        ),
                        self._high_low_rain(today),
                    ],
                ),
                # Vertical line to separate current and tomorrow weather
                # Cool gradient from black to white and back to black in non-linear fashion
                html.Div(
                    "\u00a0",  # Non-breaking space to give the div content
                    style={
                        # "height": "100%",
                        "minHeight": "80px",  # Ensure minimum height
                        "background": "linear-gradient(180deg, #000000 0%, #ffffff 50%, #000000 100%)",
                        "width": "2px",
                        "alignSelf": "stretch",  # Make it stretch to fill parent height
                        "borderRadius": "1px",
                    },
                ),
                # Tomorrow
                html.Div(
                    id=f"{self.component_id}-tomorrow-weather",
                    style={"width": "48%"},
                    children=[
                        html.Div(
                            [
                                html.Div(
                                    id=f"{self.component_id}-tomorrow-temperature",
                                    children=[
                                        html.Div(
                                            self._tomorrow_day(),
                                            className="text-ml",
                                        ),
                                    ],
                                    style={"display": "flex", "alignItems": "baseline"},
                                ),
                                dmc.Image(
                                    src=tomorrow.get("icon", ""),
                                    w=self.icon_size,
                                    h=self.icon_size,
                                ),
                            ],
                            className="centered-content",
                        ),
                        self._high_low_rain(tomorrow),
                    ],
                ),
            ],
            id=f"{self.component_id}-render-container-div",
            className="centered-content",
            style={"width": "100%", "justifyContent": "space-between"},
        )
