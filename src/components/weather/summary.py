import datetime
from typing import Any

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify


def _high_low_rain(day_data: dict[str, Any]) -> html.Div:
    """Create high/low temperature and rain chance display."""
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


def _tomorrow_day() -> str:
    """Get tomorrow's day name."""
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    return tomorrow.strftime("%a")


def render_weather_summary(
    weather_data: dict[str, Any],
    component_id: str,
    icon_size: str = "7rem",
) -> html.Div:
    """Render the weather component in Today/Tomorrow format."""
    current = weather_data.get("current", {})
    today = weather_data.get("today", {})
    tomorrow = weather_data.get("tomorrow", {})

    return html.Div(
        [
            html.Div(
                id=f"{component_id}-current-weather",
                style={"width": "48%"},
                children=[
                    html.Div(
                        [
                            html.Div(
                                id=f"{component_id}-current-temperature",
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
                                w=icon_size,
                                h=icon_size,
                            ),
                        ],
                        className="centered-content gap-m",
                    ),
                    _high_low_rain(today),
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
                id=f"{component_id}-tomorrow-weather",
                style={"width": "48%"},
                children=[
                    html.Div(
                        [
                            html.Div(
                                id=f"{component_id}-tomorrow-temperature",
                                children=[
                                    html.Div(
                                        _tomorrow_day(),
                                        className="text-ml",
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "baseline"},
                            ),
                            dmc.Image(
                                src=tomorrow.get("icon", ""),
                                w=icon_size,
                                h=icon_size,
                            ),
                        ],
                        className="centered-content",
                    ),
                    _high_low_rain(tomorrow),
                ],
            ),
        ],
        id=f"{component_id}-render-container-div",
        className="centered-content",
        style={"width": "100%", "justifyContent": "space-between"},
    )
