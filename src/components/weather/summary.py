import datetime
from typing import Any
from urllib.parse import quote

from dash import html

from utils.dates import local_today
from utils.styles import COLORS
from utils.ui import badge, icon

from .data import first_rain_hour, upcoming_hours

# The tile renders 8 hourly cells; narrow layouts hide the last two (CSS).
TILE_HOURS = 8
CHART_HOURS = 48


def render_weather_summary(
    weather_data: dict[str, Any],
    hourly_data: list[dict[str, Any]],
    daily_data: list[dict[str, Any]] | None = None,
) -> html.Div:
    """Current conditions and the next few hours on top; underneath, the
    next 48 hours as a temperature/rain chart beside the 3-day outlook.
    """
    current = weather_data.get("current", {})
    today = weather_data.get("today", {})
    chart_hours = upcoming_hours(hourly_data, CHART_HOURS)
    hours = chart_hours[:TILE_HOURS]

    now_block = html.Div(
        [
            icon(
                current.get("icon", "mdi:weather-partly-cloudy"),
                "wx-now__icon",
                current.get("icon_color"),
            ),
            html.Div(
                [
                    html.Div(
                        f"{current.get('temperature', '–')}°", className="wx-now__temp"
                    ),
                    html.Div(
                        current.get("condition", ""), className="wx-now__cond truncate"
                    ),
                    html.Div(
                        [
                            html.Span(f"H {today.get('high', '–')}°"),
                            html.Span(f"L {today.get('low', '–')}°"),
                            html.Span(f"Feels {current.get('feels_like', '–')}°"),
                        ],
                        className="wx-now__meta",
                    ),
                ],
                className="wx-now__text",
            ),
        ],
        className="wx-now",
    )

    strip = html.Div(
        [_hour_cell(h, is_now=index == 0) for index, h in enumerate(hours)],
        className="wx-hours",
    )

    return html.Div(
        [
            html.Div([now_block, strip], className="wx-top"),
            html.Div(
                [_chart(chart_hours), _outlook(daily_data or [])],
                className="wx-bottom",
            ),
        ],
        className="wx-tile",
    )


_CW, _CH = 480.0, 100.0  # chart viewBox
_RAIN_H = 30.0  # rain bars occupy the bottom of the chart


def _chart_svg(hours: list[dict[str, Any]], lo: float, hi: float) -> str:
    n = len(hours)
    step = _CW / max(n - 1, 1)
    span = (hi - lo) or 1.0
    top, bottom = 6.0, _CH - _RAIN_H - 4.0

    def y(t: float) -> float:
        return bottom - (t - lo) / span * (bottom - top)

    pts = [(i * step, y(h.get("temp_c", 0))) for i, h in enumerate(hours)]
    line = " ".join(f"{x:.1f},{yy:.1f}" for x, yy in pts)
    gold, blue = COLORS["gold"], COLORS["blue"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_CW:g} {_CH:g}" '
        'preserveAspectRatio="none">',
        "<defs><linearGradient id='t' x1='0' y1='0' x2='0' y2='1'>"
        f"<stop offset='0' stop-color='{gold}' stop-opacity='0.45'/>"
        f"<stop offset='1' stop-color='{gold}' stop-opacity='0'/>"
        "</linearGradient></defs>",
    ]
    for i, h in enumerate(hours):
        if i and h["dt"].hour == 0:
            x = i * step
            parts.append(
                f"<line x1='{x:.1f}' y1='0' x2='{x:.1f}' y2='{_CH:g}' "
                "stroke='white' stroke-opacity='0.14' stroke-dasharray='3 3' "
                "vector-effect='non-scaling-stroke'/>",
            )
        rain = h.get("rain_chance", 0) or 0
        if rain >= 5:
            bh = rain / 100 * _RAIN_H
            parts.append(
                f"<rect x='{i * step - step * 0.4:.1f}' y='{_CH - bh:.1f}' "
                f"width='{step * 0.8:.1f}' height='{bh:.1f}' rx='1' fill='{blue}' "
                f"fill-opacity='{0.35 + rain / 200:.2f}'/>",
            )
    parts.append(
        f"<polygon points='0,{bottom + 4:.1f} {line} {pts[-1][0]:.1f},{bottom + 4:.1f}' "
        "fill='url(#t)'/>",
    )
    parts.append(
        f"<polyline points='{line}' fill='none' stroke='{gold}' stroke-width='2' "
        "stroke-linejoin='round' vector-effect='non-scaling-stroke'/>",
    )
    parts.append("</svg>")
    return "".join(parts)


def _chart(hours: list[dict[str, Any]]) -> html.Div:
    """The next 48 hours: temperature line over rain-chance bars, with the
    day boundaries marked."""
    if len(hours) < 2:
        return html.Div(className="wxt-chart")
    temps = [h.get("temp_c", 0) for h in hours]
    lo, hi = min(temps), max(temps)
    n = len(hours)
    labels = [html.Span("Now", className="wxt-chart__day", style={"left": "0%"})]
    labels += [
        html.Span(
            h["dt"].strftime("%a"),
            className="wxt-chart__day",
            style={"left": f"{i / (n - 1) * 100:.1f}%"},
        )
        for i, h in enumerate(hours)
        if i and h["dt"].hour == 0
    ]
    wettest = max(hours, key=lambda h: h.get("rain_chance", 0) or 0)
    rain_note = (
        f"Rain {wettest['rain_chance']}% {wettest['dt']:%a %H:%M}"
        if (wettest.get("rain_chance") or 0) >= 30
        else "Dry"
    )
    return html.Div(
        [
            html.Div(
                [
                    html.Span("Next 48h", className="wxt-chart__title"),
                    html.Span(rain_note, className="wxt-chart__rain"),
                    html.Span(f"{lo}–{hi}°", className="wxt-chart__range"),
                ],
                className="wxt-chart__head",
            ),
            html.Img(
                src="data:image/svg+xml;charset=utf-8,"
                + quote(_chart_svg(hours, lo, hi)),
                className="wxt-chart__img",
                alt="",
            ),
            html.Div(labels, className="wxt-chart__days"),
        ],
        className="wxt-chart",
    )


def _outlook(daily: list[dict[str, Any]]) -> html.Div:
    today = local_today()
    rows = []
    for day in daily[:3]:
        date = day.get("date")
        if isinstance(date, datetime.date) and date == today:
            label = "Today"
        elif isinstance(date, datetime.date):
            label = date.strftime("%a")
        else:
            label = ""
        rain = day.get("rain_chance", 0) or 0
        rows.append(
            html.Div(
                [
                    html.Span(label, className="wxt-day__label"),
                    icon(
                        day.get("icon", "mdi:weather-partly-cloudy"),
                        "wxt-day__icon",
                        day.get("icon_color"),
                    ),
                    html.Span(
                        [icon("mdi:water", "wx-hour__drop"), f"{rain}%"],
                        className="wxt-day__rain" + (" is-wet" if rain >= 40 else ""),
                    ),
                    html.Span(
                        [
                            html.Strong(f"{day.get('high', '–')}°"),
                            html.Span(f" {day.get('low', '–')}°"),
                        ],
                        className="wxt-day__temps",
                    ),
                ],
                className="wxt-day",
            ),
        )
    return html.Div(rows, className="wxt-outlook")


def _hour_cell(hour: dict[str, Any], *, is_now: bool) -> html.Div:
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


def render_weather_badge(location: str, hourly_data: list[dict[str, Any]]):
    """A rain heads-up when it's likely in the next 12 hours - the one thing
    worth knowing on the way out of the door - otherwise the location.
    """
    next_hours = upcoming_hours(hourly_data, 12)
    rain = first_rain_hour(next_hours)
    if rain is not None:
        when = "now" if rain is next_hours[0] else rain["dt"].strftime("%H:%M")
        return badge(f"Rain likely {when}", "info", "mdi:umbrella")
    return badge(location, "neutral", "mdi:map-marker-outline") if location else None
