"""Pure-CSS sparklines for the weather summary.

Built from a single `clip-path: polygon(...)` div rather than SVG or a
charting library - Dash's `html` module has no SVG primitives, and pulling
in a new dependency (or a full Plotly figure) for a small decorative trend
indicator would be overkill next to a technique CSS already supports
natively. Percentages in `clip-path` are relative to the element's own box,
so this stays fully responsive to whatever width/height it's given.
"""

from __future__ import annotations

import datetime
from typing import Any

from dash import html

from utils.dates import local_now
from utils.styles import COLORS, FONT_SIZES


def _next_24h(hourly_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter the (today+tomorrow) hourly forecast down to the next 24h from now."""
    now = local_now()
    window_end = now + datetime.timedelta(hours=24)
    tz = now.tzinfo

    upcoming = []
    for hour in hourly_data:
        try:
            dt = datetime.datetime.fromisoformat(hour.get("time", ""))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        if now <= dt <= window_end:
            upcoming.append(hour)
    return upcoming


def _area_polygon(values: list[float], *, pad: float = 0.15) -> str:
    """A `clip-path: polygon(...)` string tracing a filled area under `values`."""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    # Pad the range so the trend doesn't touch the very top/bottom edge.
    lo -= span * pad
    hi += span * pad
    span = hi - lo

    n = len(values)
    points = [
        f"{(i / (n - 1)) * 100:.2f}% {100 - ((v - lo) / span) * 100:.2f}%"
        for i, v in enumerate(values)
    ]
    return "polygon(0% 100%, " + ", ".join(points) + ", 100% 100%)"


def _sparkline(values: list[float], *, color: str, height: str) -> html.Div:
    return html.Div(
        style={
            "height": height,
            "width": "100%",
            "background": f"linear-gradient(180deg, {color}66 0%, {color}0d 100%)",
            "clipPath": _area_polygon(values),
        },
    )


def render_weather_sparklines(hourly_data: list[dict[str, Any]]) -> html.Div | None:
    """Next-24h temperature + rain-chance mini trend charts - fills the
    horizontal space between current conditions and the today/tomorrow
    stats in the summary row with something more useful than empty space.
    """
    upcoming = _next_24h(hourly_data)
    if len(upcoming) < 2:
        return None

    temps = [h.get("temp_c", 0) for h in upcoming]
    rain = [h.get("rain_chance", 0) for h in upcoming]

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        "Next 24h",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["text_muted"],
                            "textTransform": "uppercase",
                            "letterSpacing": "0.08em",
                            "fontWeight": "700",
                        },
                    ),
                    html.Span(
                        f"{min(temps):.0f}–{max(temps):.0f}°",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["text_muted"],
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "marginBottom": "0.3rem",
                },
            ),
            _sparkline(temps, color=COLORS["gold"], height="2.1rem"),
            _sparkline(rain, color=COLORS["accent"], height="1.1rem"),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.3rem",
            "flex": "1",
            "minWidth": "9rem",
            "maxWidth": "16rem",
            "margin": "0 1.5rem",
        },
    )
