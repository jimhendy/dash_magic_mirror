import datetime
from typing import Any

from dash import html
from dash_iconify import DashIconify

from utils.dates import local_today
from utils.styles import COLORS, FONT_SIZES, WEIGHT, hero_style, kicker_style

from .sparkline import render_weather_sparklines


def _tomorrow_day() -> str:
    today = local_today()
    tomorrow = today + datetime.timedelta(days=1)
    return tomorrow.strftime("%A")


def render_weather_summary(
    weather_data: dict[str, Any],
    component_id: str,
    icon_size: str = "5.5rem",
    hourly_data: list[dict[str, Any]] | None = None,
) -> html.Div:
    """Kicker label, hero current temperature on the left, tomorrow's
    preview on the right, next-48h temperature/rain sparklines filling the
    middle - no boxes, no divider lines.
    """
    current = weather_data.get("current", {})
    tomorrow = weather_data.get("tomorrow", {})
    location = weather_data.get("location", "")
    sparklines = render_weather_sparklines(hourly_data or [])

    return html.Div(
        [
            html.Div(
                [
                    html.Span("Weather", style=kicker_style()),
                    html.Span(location, style=kicker_style(color=COLORS["text_muted"]))
                    if location
                    else None,
                ],
                style={"display": "flex", "gap": "0.8rem", "alignItems": "baseline"},
            ),
            html.Div(
                [
                    # Current conditions: hero temp + icon
                    html.Div(
                        [
                            DashIconify(
                                icon=current.get("icon", "mdi:weather-partly-cloudy"),
                                color=current.get(
                                    "icon_color",
                                    COLORS["text_secondary"],
                                ),
                                style={
                                    "width": icon_size,
                                    "height": icon_size,
                                    "flexShrink": 0,
                                },
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        f"{current.get('temperature', '?')}°",
                                        style=hero_style("4.25rem"),
                                    ),
                                    html.Div(
                                        current.get("condition", ""),
                                        style={
                                            "fontSize": FONT_SIZES["secondary"],
                                            "color": COLORS["text_secondary"],
                                            "marginTop": "0.2rem",
                                        },
                                    ),
                                ],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "1rem",
                        },
                    ),
                    # Next-48h sparklines fill the space this row otherwise
                    # leaves empty between current conditions and tomorrow's
                    # preview - they already show the high/low/rain trend,
                    # so a separate numeric readout would be redundant.
                    sparklines,
                    # Tomorrow preview
                    html.Div(
                        [
                            DashIconify(
                                icon=tomorrow.get("icon", "mdi:weather-partly-cloudy"),
                                color=tomorrow.get(
                                    "icon_color", COLORS["text_secondary"]
                                ),
                                style={
                                    "width": "2.75rem",
                                    "height": "2.75rem",
                                    "opacity": 0.8,
                                },
                            ),
                            html.Span(
                                _tomorrow_day()[:3],
                                style={
                                    "fontSize": FONT_SIZES["small"],
                                    "color": COLORS["text_muted"],
                                    "fontWeight": WEIGHT["semibold"],
                                    "textTransform": "uppercase",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                            "gap": "0.2rem",
                        },
                    ),
                ],
                id=f"{component_id}-render-container-div",
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "width": "100%",
                },
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.6rem",
            "width": "100%",
        },
    )
