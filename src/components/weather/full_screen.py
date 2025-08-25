import datetime
from dataclasses import dataclass
from typing import Any

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import dcc, html
from dash_iconify import DashIconify

from utils.styles import COLORS


def _format_day_name(date_str: str) -> str:
    """Format date to day name (e.g., '2025-08-25' -> 'Sunday')."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        if dt.date() == datetime.date.today():
            return "Today"
        if dt.date() == datetime.date.today() + datetime.timedelta(days=1):
            return "Tomorrow"
        return dt.strftime("%A")
    except:
        return date_str


@dataclass
class HourlyWeather:
    time: datetime.datetime
    temp_c: float
    feels_like: float
    rain_chance: float
    icon: str
    condition: str
    cloud_cover: float


def _create_hourly_timeseries(
    hourly_data: list[dict[str, Any]],
    daily_data: list[dict[str, Any]],
    font_size: int = 20,
) -> go.Figure:
    """Create a timeseries plot for hourly weather data."""
    if not hourly_data:
        return go.Figure()

    # Extract data for plotting
    hour_data = []
    now = datetime.datetime.now()
    tomorrow = now + datetime.timedelta(days=1)

    for hour in hourly_data:  # Show 24 hours
        dt = datetime.datetime.fromisoformat(hour.get("time", ""))
        if dt < now or dt >= tomorrow:
            continue
        hour_data.append(
            HourlyWeather(
                time=dt,
                temp_c=hour.get("temp_c", 0),
                feels_like=hour.get("feels_like", 0),
                rain_chance=hour.get("rain_chance", 0),
                icon=hour.get("icon", ""),
                condition=hour.get("condition", ""),
                cloud_cover=hour.get("cloud", 0),
            ),
        )

    hour_data.sort(key=lambda x: x.time)  # Ensure sorted by time

    if not hour_data:
        return go.Figure()

    # Create single plot (no subplots)
    fig = go.Figure()

    # Rain chance area (right axis, blue)
    fig.add_trace(
        go.Scatter(
            x=[hd.time for hd in hour_data],
            y=[hd.rain_chance for hd in hour_data],
            mode="lines",
            name="Rain Chance",
            line=dict(color=COLORS["blue"], width=2),
            yaxis="y2",
            line_shape="spline",
        ),
    )

    # Cloud cover (right axis, gray)
    fig.add_trace(
        go.Scatter(
            x=[hd.time for hd in hour_data],
            y=[hd.cloud_cover for hd in hour_data],
            mode="lines",
            name="Cloud Cover",
            line=dict(color=COLORS["gray"], width=2, dash="dot"),
            yaxis="y2",
            line_shape="spline",
        ),
    )

    # Temperature line
    fig.add_trace(
        go.Scatter(
            x=[hd.time for hd in hour_data],
            y=[hd.temp_c for hd in hour_data],
            mode="lines",
            name="Temperature",
            line=dict(color=COLORS["red"], width=4),
        ),
    )

    # Feels like temperature (subtle line)
    fig.add_trace(
        go.Scatter(
            x=[hd.time for hd in hour_data],
            y=[hd.feels_like for hd in hour_data],
            mode="lines",
            name="Feels Like",
            line=dict(color=COLORS["dimmed_red"], width=2, dash="dot"),
        ),
    )

    # Maximized layout with no legend and tight margins
    fig.update_layout(
        height=None,  # Let the container control height
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", size=font_size, family="Inter"),
        showlegend=False,  # Show legend
        margin=dict(l=40, r=40, t=20, b=40),  # Tight margins for maximum space
        hovermode=None,
        # Adjust y-axis range for tighter layout without icons/annotations at top
        yaxis=dict(
            range=[
                min(hd.temp_c for hd in hour_data) - 1,
                max(hd.temp_c for hd in hour_data) + 1,
            ],
        ),
        autosize=True,  # Let the chart resize to fit container
    )

    # Clean up axes
    fig.update_xaxes(
        showgrid=False,
        tickformat="%-I %p",
        tickangle=0,
        color="white",
        linecolor="rgba(255,255,255,0.3)",
        dtick=4 * 3600000,  # Every 4 hours
        tickfont=dict(size=font_size),
        title=None,
    )

    # Temperature axis (left)
    fig.update_yaxes(
        title=None,
        ticksuffix="°C",
        color=COLORS["red"],
        linecolor=COLORS["red"],
        tickcolor=COLORS["red"],
        tickfont=dict(size=font_size, color=COLORS["red"]),
        side="left",
        showgrid=False,
    )

    # Rain chance axis (right)
    fig.update_layout(
        yaxis2=dict(
            title=None,
            ticksuffix="%",
            overlaying="y",
            side="right",
            color=COLORS["blue"],
            linecolor=COLORS["blue"],
            tickcolor=COLORS["blue"],
            range=[0, 100],
            tickfont=dict(size=font_size, color=COLORS["blue"]),
            showgrid=False,
        ),
    )

    # Add a vertical dim gray line if the x-axis crosses a day boundry
    for i in range(1, len(hour_data)):
        if hour_data[i].time.date() != hour_data[i - 1].time.date():
            fig.add_vline(
                x=hour_data[i].time,
                line=dict(color=COLORS["gray"], width=2, dash="dot"),
            )

    # Add a sunrise and sunset symbols at the top of the plot (assuming it will not be peak temp)
    # Sunrise and sunset are in the daily_data so need to extract based on the current x-axis
    days = set(hd.time.date() for hd in hour_data)
    sunrises = [
        dd.get("sunrise", "") for dd in daily_data if dd.get("date", "") in days
    ]
    sunsets = [dd.get("sunset", "") for dd in daily_data if dd.get("date", "") in days]
    for sr in sunrises:
        if sr < now or sr >= tomorrow:
            continue
        fig.add_annotation(
            x=sr,
            y=max(hd.temp_c for hd in hour_data) + 1,
            text=f"☀️ {sr.strftime('%I:%M')}",
            showarrow=False,
            font=dict(size=20),
        )
    for ss in sunsets:
        if ss < now or ss >= tomorrow:
            continue
        fig.add_annotation(
            x=ss,
            y=max(hd.temp_c for hd in hour_data) + 1,
            text=f"☽ {ss.strftime('%I:%M')}",
            showarrow=False,
            font=dict(size=20),
        )

    return fig


def _render_daily_item(day_data: dict[str, Any]) -> html.Div:
    """Render a single daily forecast item."""
    return html.Div(
        [
            # Day name
            html.Div(
                _format_day_name(day_data.get("date", "")),
                style={"fontWeight": "500"},
                className="text-ms",
            ),
            # Weather icon and condition
            html.Div(
                [
                    dmc.Image(
                        src=day_data.get("icon", ""),
                        w="2.5rem",
                        h="2.5rem",
                        style={"marginRight": "0.75rem"},
                    ),
                    html.Div(
                        [
                            html.Div(
                                day_data.get("condition", ""),
                                className="text-ms",
                            ),
                            html.Div(
                                f"UV: {day_data.get('uv_index', 0)}",
                                className="text-s",
                                style={"color": "#aaa", "fontSize": "0.75rem", "marginTop": "0.25rem"},
                            ),
                        ],
                        style={"flex": "1", "textAlign": "left"},
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "width": "12rem"},
            ),
            # High/Low temperatures
            html.Div(
                [
                    html.Span(
                        f"{day_data.get('high', 0)}°",
                        style={"fontWeight": "bold", "marginRight": "0.5rem"},
                    ),
                    html.Span(
                        f"{day_data.get('low', 0)}°",
                        style={"color": "#888", "marginRight": "1rem"},
                    ),
                ],
                style={"width": "4rem", "textAlign": "right"},
                className="text-ms",
            ),
            # Rain chance and precipitation
            html.Div(
                [
                    html.Div(
                        [
                            DashIconify(
                                icon="mdi:water-percent",
                                color="#5f9fff",
                                style={"marginRight": "0.25rem"},
                            ),
                            html.Span(f"{day_data.get('rain_chance', 0)}%"),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "marginBottom": "0.25rem",
                        },
                        className="text-ms",
                    ),
                    html.Div(
                        f"{day_data.get('total_precip', 0):.1f}mm",
                        style={"color": "#aaa", "fontSize": "0.75rem"},
                    )
                    if day_data.get("total_precip", 0) > 0
                    else None,
                ],
                style={"width": "3.5rem", "textAlign": "center"},
            ),
            # Wind
            html.Div(
                [
                    DashIconify(
                        icon="mdi:weather-windy",
                        color="#aaa",
                        style={"marginRight": "0.25rem"},
                    ),
                    html.Span(f"{day_data.get('max_wind', 0)} mph"),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "width": "4rem",
                    "justifyContent": "center",
                },
                className="text-ms",
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
            "padding": "0.5rem 1rem",  # Reduced padding
            "backgroundColor": "rgba(255, 255, 255, 0.05)",
            "borderRadius": "0.25rem",  # Smaller radius
            "margin": "0.125rem 0",  # Smaller margin
            "width": "100%",
            "border": "1px solid rgba(255, 255, 255, 0.1)",
            "height": "30%",
        },
        className="daily-item",
    )


def render_weather_fullscreen(
    weather_data: dict[str, Any],
    component_id: str,
) -> html.Div:
    """SIMPLE weather fullscreen - NO COMPLICATIONS."""
    hourly_data = weather_data.get("hourly", [])
    daily_data = weather_data.get("daily", [])

    return html.Div(
        [
            # # Header: 60px
            # html.Div(
            #     [
            #         html.Span(
            #             location,
            #             style={"fontSize": "2rem", "marginRight": "2rem"},
            #         ),
            #         html.Span(
            #             f"{current.get('temperature', 0)}°C",
            #             style={"fontSize": "2rem", "marginRight": "2rem"},
            #         ),
            #         html.Span(
            #             current.get("condition", ""),
            #             style={"fontSize": "1.5rem", "color": "#ccc"},
            #         ),
            #     ],
            #     style={
            #         "display": "flex",
            #         "alignItems": "center",
            #         "justifyContent": "center",
            #         "height": "60px",
            #         "padding": "0.5rem",
            #         "borderBottom": "1px solid rgba(255,255,255,0.1)",
            #     },
            # ),
            # Chart: Everything else minus 180px for forecast
            html.Div(
                [
                    dcc.Graph(
                        figure=_create_hourly_timeseries(hourly_data, daily_data),
                        config={
                            "displayModeBar": False,
                            "responsive": True,
                            "staticPlot": True,
                        },
                        style={"height": "100%", "width": "100%"},
                    ),
                ],
                style={
                    "height": "66%",
                },
            ),
            # Daily Forecast
            html.Div(
                [
                    _render_daily_item(day)
                    for day in daily_data
                ],
                style={"height": "30%"},
            ),
        ],
        style={
            "height": "100vh",
            "color": "white",
            "backgroundColor": "black",
            "fontFamily": "Inter, sans-serif",
            "overflow": "hidden",
            "display": "flex",
            "flexDirection": "column",
        },
        id=f"{component_id}-fullscreen",
    )
