import datetime
import os

import httpx
from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.file_cache import cache_json


class Weather(BaseComponent):
    """Weather component for the Magic Mirror application.
    Displays current weather, chance of rain, and 3-day forecast for a given UK postcode.

    Uses WeatherAPI.com for weather data.
    Requires a free API key from https://www.weatherapi.com/signup.aspx
    """

    def __init__(self, postcode: str, *args, **kwargs):
        super().__init__(name="weather", *args, **kwargs)
        self.postcode = postcode.upper().replace(" ", "")
        self.api_key = os.environ.get("WEATHER_API_KEY")
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
                        "fontFamily": "Arial, sans-serif",
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
                weather_data = self.fetch()
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

            weather_data = response.json()
            return self._process_weather_data(weather_data)

        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return self._get_mock_data()

    def _process_weather_data(self, raw_data: dict) -> dict:
        """Process raw WeatherAPI data into our format."""
        processed = {
            "current": {},
            "forecast": [],
            "location": raw_data.get("location", {}).get("name", self.postcode),
        }

        # Current weather
        current = raw_data.get("current", {})
        if current:
            processed["current"] = {
                "temperature": round(current.get("temp_c", 0)),
                "description": current.get("condition", {}).get("text", "Unknown"),
                "humidity": current.get("humidity", 0),
                "rain_chance": 0,  # Current weather doesn't have rain chance
                "icon": current.get("condition", {}).get("icon", ""),
            }

        # Process forecast for next 3 days
        forecast_days = raw_data.get("forecast", {}).get("forecastday", [])
        for i, day_data in enumerate(forecast_days[1:4]):  # Skip today, get next 3 days
            day_forecast = day_data.get("day", {})
            if day_forecast:
                processed["forecast"].append(
                    {
                        "day": self._format_day(day_data.get("date", ""), i + 1),
                        "high": round(day_forecast.get("maxtemp_c", 0)),
                        "low": round(day_forecast.get("mintemp_c", 0)),
                        "rain_chance": day_forecast.get("daily_chance_of_rain", 0),
                        "condition": day_forecast.get("condition", {}).get(
                            "text",
                            "Unknown",
                        ),
                    },
                )

        # If we have today's data, use it for rain chance
        if forecast_days:
            today_forecast = forecast_days[0].get("day", {})
            processed["current"]["rain_chance"] = today_forecast.get(
                "daily_chance_of_rain",
                0,
            )

        return processed

    def _format_day(self, date_str: str, days_ahead: int) -> str:
        """Format day name for forecast."""
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            if days_ahead == 1:
                return "Tomorrow"
            return date_obj.strftime("%A")[:3]  # Mon, Tue, etc.
        except:  # noqa: E722
            return f"Day {days_ahead}"

    def _get_mock_data(self) -> dict:
        """Return mock data when API is unavailable."""
        return {
            "current": {
                "temperature": 18,
                "description": "Partly Cloudy",
                "humidity": 65,
                "rain_chance": 30,
                "icon": "02d",
            },
            "forecast": [
                {
                    "day": "Tomorrow",
                    "high": 20,
                    "low": 12,
                    "rain_chance": 10,
                    "condition": "Clear",
                },
                {
                    "day": "Wed",
                    "high": 22,
                    "low": 14,
                    "rain_chance": 5,
                    "condition": "Clear",
                },
                {
                    "day": "Thu",
                    "high": 19,
                    "low": 11,
                    "rain_chance": 60,
                    "condition": "Rain",
                },
            ],
            "location": self.postcode,
        }

    def _render_weather(self, weather_data: dict) -> html.Div:
        """Render the weather component."""
        current = weather_data.get("current", {})
        forecast = weather_data.get("forecast", [])

        return html.Div(
            [
                # Header with location
                html.Div(
                    [
                        html.Span("☀️ ", style={"fontSize": "16px"}),
                        html.Span(
                            weather_data.get("location", "Weather"),
                            style={"fontWeight": "bold", "fontSize": "16px"},
                        ),
                    ],
                    style={"marginBottom": "8px"},
                ),
                # Current weather
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span(
                                    f"{current.get('temperature', '--')}°C",
                                    style={"fontSize": "24px", "fontWeight": "bold"},
                                ),
                                html.Br(),
                                html.Span(
                                    current.get("description", "Unknown"),
                                    style={"fontSize": "12px", "opacity": "0.8"},
                                ),
                            ],
                            style={"marginBottom": "6px"},
                        ),
                        html.Div(
                            [
                                html.Span(
                                    f"💧 {current.get('rain_chance', 0)}%",
                                    style={"fontSize": "12px", "marginRight": "10px"},
                                ),
                                html.Span(
                                    f"💨 {current.get('humidity', 0)}%",
                                    style={"fontSize": "12px"},
                                ),
                            ],
                            style={"marginBottom": "10px", "opacity": "0.7"},
                        ),
                    ],
                ),
                # 3-day forecast
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    day["day"],
                                    style={
                                        "fontSize": "11px",
                                        "fontWeight": "bold",
                                        "marginBottom": "2px",
                                    },
                                ),
                                html.Div(
                                    f"{day['high']}°/{day['low']}°",
                                    style={"fontSize": "11px", "marginBottom": "1px"},
                                ),
                                html.Div(
                                    f"💧{day['rain_chance']}%",
                                    style={"fontSize": "10px", "opacity": "0.6"},
                                ),
                            ],
                            style={
                                "display": "inline-block",
                                "margin": "0 8px",
                                "textAlign": "center",
                                "verticalAlign": "top",
                                "minWidth": "40px",
                            },
                        )
                        for day in forecast[:3]
                    ],
                    style={
                        "borderTop": "1px solid rgba(255,255,255,0.2)",
                        "paddingTop": "8px",
                        "marginTop": "8px",
                    },
                ),
            ],
        )
