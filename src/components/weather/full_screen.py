import datetime
from typing import Any

import plotly.graph_objects as go
from dash import dcc, html

from utils.dates import local_today
from utils.styles import COLORS, FONT_FAMILY, with_alpha
from utils.ui import icon, section, stat

from .data import upcoming_hours

CHART_HOURS = 24


def render_weather_fullscreen(weather_data: dict[str, Any]) -> html.Div:
    current = weather_data.get("current", {})
    hourly = weather_data.get("hourly", [])
    daily = weather_data.get("daily", [])
    today = daily[0] if daily else {}
    hours = upcoming_hours(hourly, CHART_HOURS)

    return html.Div(
        [
            html.Div(
                [_now_card(current), _stats(current, today)],
                className="wx-detail__top",
            ),
            section(
                "Next 24 hours",
                html.Div(
                    [
                        html.Div(
                            [
                                _hour_column(h, index == 0)
                                for index, h in enumerate(hours)
                            ],
                            className="wx-scroll hscroll",
                        ),
                        html.Div(
                            dcc.Graph(
                                figure=_hourly_chart(hours),
                                config={
                                    "displayModeBar": False,
                                    "responsive": True,
                                    "staticPlot": True,
                                },
                                className="wx-chart__graph",
                            ),
                            className="wx-chart",
                        )
                        if len(hours) > 1
                        else None,
                    ],
                ),
                class_name="card",
            ),
            section(
                f"{len(daily)}-day forecast",
                _daily_rows(daily),
                class_name="card",
            ),
        ],
        className="detail wx-detail",
    )


def _now_card(current: dict[str, Any]) -> html.Div:
    return html.Div(
        [
            icon(
                current.get("icon", "mdi:weather-partly-cloudy"),
                "wx-big__icon",
                current.get("icon_color"),
            ),
            html.Div(
                [
                    html.Div(
                        f"{current.get('temperature', '–')}°", className="wx-big__temp"
                    ),
                    html.Div(current.get("condition", ""), className="wx-big__cond"),
                    html.Div(
                        f"Feels like {current.get('feels_like', '–')}°",
                        className="wx-big__feels",
                    ),
                ],
            ),
        ],
        className="card wx-big",
    )


def _fmt_time(value: Any) -> str:
    return value.strftime("%H:%M") if isinstance(value, datetime.datetime) else "–"


def _stats(current: dict[str, Any], today: dict[str, Any]) -> html.Div:
    wind = f"{current.get('wind_mph', '–')} mph {current.get('wind_dir', '')}".strip()
    return html.Div(
        [
            stat("Wind", wind, "mdi:weather-windy"),
            stat("Humidity", f"{current.get('humidity', '–')}%", "mdi:water-percent"),
            stat(
                "Rain today",
                f"{today.get('rain_chance', '–')}%",
                "mdi:umbrella-outline",
            ),
            stat(
                "UV index",
                f"{current.get('uv', today.get('uv_index', '–'))}",
                "mdi:white-balance-sunny",
            ),
            stat("Sunrise", _fmt_time(today.get("sunrise")), "mdi:weather-sunset-up"),
            stat("Sunset", _fmt_time(today.get("sunset")), "mdi:weather-sunset-down"),
        ],
        className="card stat-grid",
    )


def _hour_column(hour: dict[str, Any], is_now: bool) -> html.Div:
    rain = hour.get("rain_chance", 0)
    return html.Div(
        [
            html.Div(
                "Now" if is_now else hour["dt"].strftime("%H:%M"),
                className="wx-hour__time",
            ),
            icon(
                hour.get("icon", "mdi:weather-partly-cloudy"),
                "wx-hour__icon",
                hour.get("icon_color"),
            ),
            html.Div(f"{hour.get('temp_c', '–')}°", className="wx-hour__temp"),
            html.Div(
                [icon("mdi:water", "wx-hour__drop"), f"{rain}%"],
                className="wx-hour__rain" + (" is-wet" if rain >= 40 else ""),
            ),
        ],
        className="wx-hour" + (" is-now" if is_now else ""),
    )


def _hourly_chart(hours: list[dict[str, Any]]) -> go.Figure:
    """Temperature line over rain-chance bars for the next 24 hours."""
    times = [h["dt"] for h in hours]
    temps = [h.get("temp_c", 0) for h in hours]
    rain = [h.get("rain_chance", 0) for h in hours]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=times,
            y=rain,
            yaxis="y2",
            marker=dict(color=with_alpha(COLORS["blue"], 0.45), line=dict(width=0)),
            name="Rain",
        ),
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=temps,
            mode="lines",
            line=dict(color=COLORS["gold"], width=3, shape="spline", smoothing=0.6),
            name="Temperature",
        ),
    )
    # Midnight divider when the 24h window crosses into tomorrow.
    for prev, cur in zip(times, times[1:], strict=False):
        if cur.date() != prev.date():
            fig.add_vline(
                x=cur, line=dict(color=COLORS["hairline_strong"], width=1, dash="dot")
            )

    lo, hi = min(temps), max(temps)
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_secondary"], size=13, family=FONT_FAMILY),
        showlegend=False,
        margin=dict(l=36, r=40, t=10, b=28),
        bargap=0.35,
        autosize=True,
        xaxis=dict(
            showgrid=False,
            tickformat="%H:%M",
            dtick=3 * 3600000,
            linecolor=COLORS["hairline_strong"],
        ),
        yaxis=dict(
            range=[lo - 1.5, hi + 1.5],
            ticksuffix="°",
            showgrid=True,
            gridcolor=COLORS["hairline"],
            zeroline=False,
            tickfont=dict(color=COLORS["gold"]),
            nticks=5,
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            range=[0, 100],
            ticksuffix="%",
            showgrid=False,
            zeroline=False,
            tickfont=dict(color=COLORS["blue"]),
            nticks=3,
        ),
    )
    return fig


def _daily_rows(daily: list[dict[str, Any]]) -> html.Div:
    if not daily:
        return html.Div()
    lo = min(d.get("low", 0) for d in daily)
    hi = max(d.get("high", 0) for d in daily)
    span = (hi - lo) or 1
    today = local_today()

    rows = []
    for d in daily:
        date = d.get("date")
        if date == today:
            name = "Today"
        elif date == today + datetime.timedelta(days=1):
            name = "Tomorrow"
        else:
            name = date.strftime("%A") if date else ""
        left = (d.get("low", 0) - lo) / span * 100
        width = (d.get("high", 0) - d.get("low", 0)) / span * 100
        rows.append(
            html.Div(
                [
                    html.Div(name, className="wx-day__name"),
                    icon(
                        d.get("icon", "mdi:weather-partly-cloudy"),
                        "wx-day__icon",
                        d.get("icon_color"),
                    ),
                    html.Div(d.get("condition", ""), className="wx-day__cond truncate"),
                    html.Div(
                        [
                            icon("mdi:water", "wx-hour__drop"),
                            f"{d.get('rain_chance', 0)}%",
                        ],
                        className="wx-day__rain"
                        + (" is-wet" if d.get("rain_chance", 0) >= 40 else ""),
                    ),
                    html.Div(f"{d.get('low', '–')}°", className="wx-day__low"),
                    html.Div(
                        html.Div(
                            className="range__fill",
                            style={
                                "left": f"{left:.1f}%",
                                "width": f"{max(width, 4):.1f}%",
                            },
                        ),
                        className="range",
                    ),
                    html.Div(f"{d.get('high', '–')}°", className="wx-day__high"),
                ],
                className="wx-day",
            ),
        )
    return html.Div(rows, className="wx-days")
