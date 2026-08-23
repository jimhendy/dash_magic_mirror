import datetime
from dataclasses import dataclass
from typing import Any

import plotly.graph_objects as go
from dash import dcc, html
from dash_iconify import DashIconify

from utils.dates import get_app_timezone, local_now
from utils.styles import COLORS, FONT_FAMILY, SPACE, row_style


def _with_alpha(hex_color: str, alpha: float) -> str:
    """`#RRGGBB` -> `rgba(r, g, b, alpha)` - Plotly fill colors need an
    explicit rgba string, unlike the CSS hex-alpha-suffix trick used
    elsewhere in this app.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def _format_day_name(date: str | datetime.date | datetime.datetime) -> str:
    """Format date to day name (e.g., '2025-08-25' -> '25th')."""
    if isinstance(date, datetime.date):
        pass
    elif isinstance(date, str):
        date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    elif isinstance(date, datetime.datetime):
        date = date.date()
    else:
        msg = f"Invalid date type: {type(date)}"
        raise ValueError(msg)

    day = date.day
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


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
    line_shape: str = "hv",
) -> go.Figure:
    """Create a timeseries plot for hourly weather data."""
    if not hourly_data:
        return go.Figure()

    # Extract data for plotting
    hour_data = []
    now = local_now()
    tomorrow = now + datetime.timedelta(days=1)
    tz = get_app_timezone()

    for hour in hourly_data:  # Show 24 hours
        dt = datetime.datetime.fromisoformat(hour.get("time", ""))
        # Ensure timezone-aware in app timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
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

    temp_color = COLORS["gold"]
    rain_color = COLORS["accent"]
    cloud_color = COLORS["text_secondary"]

    # Create single plot (no subplots)
    fig = go.Figure()

    # Cloud cover: a soft ambient backdrop (area only, no visible line),
    # added first so it renders behind the rain/temperature traces.
    fig.add_trace(
        go.Scatter(
            x=[hd.time for hd in hour_data],
            y=[hd.cloud_cover for hd in hour_data],
            mode="lines",
            name="Cloud Cover",
            line=dict(color=cloud_color, width=0),
            fill="tozeroy",
            fillcolor=_with_alpha(cloud_color, 0.14),
            yaxis="y2",
            line_shape=line_shape,
            hoverinfo="skip",
        ),
    )

    # Rain chance: area + line, matching the summary sparkline's styling.
    fig.add_trace(
        go.Scatter(
            x=[hd.time for hd in hour_data],
            y=[hd.rain_chance for hd in hour_data],
            mode="lines",
            name="Rain Chance",
            line=dict(color=rain_color, width=2),
            fill="tozeroy",
            fillcolor=_with_alpha(rain_color, 0.22),
            yaxis="y2",
            line_shape=line_shape,
        ),
    )

    # Temperature: the dominant signal - a clean bold line reads clearly on
    # its own, so it's left unfilled rather than tinting the whole chart.
    fig.add_trace(
        go.Scatter(
            x=[hd.time for hd in hour_data],
            y=[hd.temp_c for hd in hour_data],
            mode="lines",
            name="Temperature",
            line=dict(color=temp_color, width=4),
        ),
    )

    # Maximized layout with no legend and tight margins
    fig.update_layout(
        height=None,  # Let the container control height
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"], size=font_size, family=FONT_FAMILY),
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
        color=COLORS["text_secondary"],
        linecolor=COLORS["hairline_strong"],
        dtick=4 * 3600000,  # Every 4 hours
        tickfont=dict(size=font_size),
        title=None,
    )

    # Temperature axis (left)
    fig.update_yaxes(
        title=None,
        ticksuffix="°C",
        color=temp_color,
        linecolor=temp_color,
        tickcolor=temp_color,
        tickfont=dict(size=font_size, color=temp_color),
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
            color=rain_color,
            linecolor=rain_color,
            tickcolor=rain_color,
            range=[0, 100],
            tickfont=dict(size=font_size, color=rain_color),
            showgrid=False,
        ),
    )

    # Add a dim divider line if the x-axis crosses a day boundary
    for i in range(1, len(hour_data)):
        if hour_data[i].time.date() != hour_data[i - 1].time.date():
            fig.add_vline(
                x=hour_data[i].time,
                line=dict(color=COLORS["text_muted"], width=2, dash="dash"),
            )

    # Add a sunrise and sunset symbols at the top of the plot (assuming it will not be peak temp)
    # Sunrise and sunset are in the daily_data so need to extract based on the current x-axis
    days = set(hd.time.date() for hd in hour_data)
    sunrises = [
        dd.get("sunrise", "") for dd in daily_data if dd.get("date", "") in days
    ]
    sunsets = [dd.get("sunset", "") for dd in daily_data if dd.get("date", "") in days]
    for sr in sunrises:
        if not isinstance(sr, datetime.datetime):
            continue
        sr_dt = sr if sr.tzinfo is not None else sr.replace(tzinfo=tz)
        if sr_dt < now or sr_dt >= tomorrow:
            continue
        fig.add_annotation(
            x=sr_dt,
            y=max(hd.temp_c for hd in hour_data) + 1,
            text=f"☀️ {sr_dt.strftime('%-H:%M')}",
            showarrow=False,
            font=dict(size=20),
        )
    for ss in sunsets:
        if not isinstance(ss, datetime.datetime):
            continue
        ss_dt = ss if ss.tzinfo is not None else ss.replace(tzinfo=tz)
        if ss_dt < now or ss_dt >= tomorrow:
            continue
        fig.add_annotation(
            x=ss_dt,
            y=max(hd.temp_c for hd in hour_data) + 1,
            text=f"☽ {ss_dt.strftime('%H:%M')}",
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
                style={"fontWeight": "600", "color": COLORS["text"]},
                className="text-ms",
            ),
            # Weather icon and condition
            html.Div(
                [
                    DashIconify(
                        icon=day_data.get("icon", "mdi:weather-partly-cloudy"),
                        color=day_data.get("icon_color", COLORS["text_secondary"]),
                        style={
                            "width": "2.5rem",
                            "height": "2.5rem",
                            "marginRight": "0.75rem",
                        },
                    ),
                    html.Div(
                        [
                            html.Div(
                                day_data.get("condition", ""),
                                className="text-ms",
                                style={"color": COLORS["text"]},
                            ),
                            html.Div(
                                f"UV: {day_data.get('uv_index', 0)}",
                                className="text-s",
                                style={
                                    "color": COLORS["text_muted"],
                                    "fontSize": "0.75rem",
                                    "marginTop": "0.25rem",
                                },
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
                        style={
                            "fontWeight": "700",
                            "marginRight": "0.5rem",
                            "color": COLORS["gold"],
                        },
                    ),
                    html.Span(
                        f"{day_data.get('low', 0)}°",
                        style={
                            "color": COLORS["text_secondary"],
                            "marginRight": "1rem",
                        },
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
                                color=COLORS["accent"],
                                style={"marginRight": "0.25rem"},
                            ),
                            html.Span(
                                f"{day_data.get('rain_chance', 0)}%",
                                style={"color": COLORS["text"]},
                            ),
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
                        style={"color": COLORS["text_muted"], "fontSize": "0.75rem"},
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
                        color=COLORS["text_secondary"],
                        style={"marginRight": "0.25rem"},
                    ),
                    html.Span(
                        f"{day_data.get('max_wind', 0)} mph",
                        style={"color": COLORS["text"]},
                    ),
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
        style=row_style(
            divider=True,
            display="flex",
            alignItems="center",
            justifyContent="space-between",
            width="100%",
            height="30%",
        ),
        className="daily-item",
    )


def render_weather_fullscreen(
    weather_data: dict[str, Any],
    component_id: str,
) -> html.Div:
    hourly_data = weather_data.get("hourly", [])
    daily_data = weather_data.get("daily", [])

    return html.Div(
        [
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
                style={"height": "66%"},
            ),
            # Daily Forecast
            html.Div(
                [_render_daily_item(day) for day in daily_data],
                style={"height": "30%", "padding": f"0 {SPACE['lg']}"},
            ),
        ],
        style={
            "height": "100%",
            "color": COLORS["text"],
            "background": COLORS["bg"],
            "display": "flex",
            "flexDirection": "column",
        },
        id=f"{component_id}-fullscreen",
    )
