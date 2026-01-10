import datetime
from typing import Any

import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from utils.dates import local_today
from utils.styles import FONT_SIZES

_HRL_MARGIN = "5px"


def _high_low_rain_compact(day_data: dict[str, Any]) -> html.Div:
    """Create compact vertical stack of high/low/rain numbers only (no icons)."""
    high = day_data.get("high", "?")
    low = day_data.get("low", "?")
    rain = day_data.get("rain_chance", "?")

    return html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.3rem",
            "justifyContent": "center",
            "alignItems": "center",
            "minWidth": "3.5rem",
        },
        children=[
            # High
            html.Span(
                str(high) + "°",
                style={
                    "fontSize": "1.6rem",
                    "fontWeight": "600",
                    "lineHeight": "1",
                    "color": "#ff6b6b",
                    "margin": _HRL_MARGIN,
                },
            ),
            # Rain
            html.Span(
                str(rain) + "%",
                style={
                    "fontSize": "1.6rem",
                    "fontWeight": "600",
                    "lineHeight": "1",
                    "color": "#6ec6ff",
                    "margin": _HRL_MARGIN,
                },
            ),
            # Low
            html.Span(
                str(low) + "°",
                style={
                    "fontSize": "1.6rem",
                    "fontWeight": "600",
                    "lineHeight": "1",
                    "color": "#5f9fff",
                    "margin": _HRL_MARGIN,
                },
            ),
        ],
    )


def _central_divider_with_icons() -> html.Div:
    """Create central divider with high/rain/low icons as separators."""
    return html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.3rem",
            "justifyContent": "center",
            "alignItems": "center",
            "padding": "0 0.3rem",
        },
        children=[
            # High icon
            DashIconify(
                icon="mdi:arrow-up",
                color="#ff6b6b",
                width=24,
                height=24,
                style={"margin": _HRL_MARGIN},
            ),
            # Rain icon
            DashIconify(
                icon="mdi:weather-rainy",
                color="#6ec6ff",
                width=24,
                height=24,
                style={"margin": _HRL_MARGIN},
            ),
            # Low icon
            DashIconify(
                icon="mdi:arrow-down",
                color="#5f9fff",
                width=24,
                height=24,
                style={"margin": _HRL_MARGIN},
            ),
        ],
    )


def _tomorrow_day() -> str:
    """Get tomorrow's day name."""
    today = local_today()
    tomorrow = today + datetime.timedelta(days=1)
    return tomorrow.strftime("%a")


def render_weather_summary(
    weather_data: dict[str, Any],
    component_id: str,
    icon_size: str = "7rem",
) -> html.Div:
    """Render the weather component with central icon divider and flanking stats."""
    current = weather_data.get("current", {})
    today = weather_data.get("today", {})
    tomorrow = weather_data.get("tomorrow", {})

    return html.Div(
        [
            # Left half: Today's current temp and weather icon (centered)
            html.Div(
                [
                    html.Div(
                        id=f"{component_id}-current-temperature",
                        children=[
                            html.Div(
                                current.get("temperature", "?"),
                                style={
                                    "fontSize": "4rem",
                                    "fontWeight": "350",
                                },
                            ),
                            html.Div(
                                "°C",
                                style={
                                    "fontSize": FONT_SIZES["summary_secondary"],
                                    "marginLeft": "4px",
                                },
                                className="degrees",
                            ),
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
                style={"flex": "1"},
            ),
            # Today's stats (right side of left half, close to divider)
            _high_low_rain_compact(today),
            # Central divider with icons (high, rain, low)
            _central_divider_with_icons(),
            # Tomorrow's stats (left side of right half, close to divider)
            _high_low_rain_compact(tomorrow),
            # Right half: Tomorrow's day name and weather icon (centered)
            html.Div(
                [
                    html.Div(
                        id=f"{component_id}-tomorrow-temperature",
                        children=[
                            html.Div(
                                _tomorrow_day(),
                                style={
                                    "fontSize": FONT_SIZES["summary_primary"],
                                    "fontWeight": "350",
                                },
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
                style={"flex": "1"},
            ),
        ],
        id=f"{component_id}-render-container-div",
        className="centered-content",
        style={
            "width": "100%",
            "justifyContent": "space-between",
            "alignItems": "center",
        },
    )
