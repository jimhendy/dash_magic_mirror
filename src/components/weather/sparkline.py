"""Weather-specific sparkline assembly - the actual sparkline mechanics
(clip-path polygons) live in `utils.sparkline`, shared with the markets
component.
"""

from __future__ import annotations

import datetime
from typing import Any

from dash import html

from utils.dates import local_now
from utils.sparkline import sparkline
from utils.styles import COLORS, FONT_SIZES

SPARKLINE_HOURS = 48


def _next_hours(
    hourly_data: list[dict[str, Any]],
    hours: int = SPARKLINE_HOURS,
) -> list[dict[str, Any]]:
    """Filter the hourly forecast down to the next `hours` from now."""
    now = local_now()
    window_end = now + datetime.timedelta(hours=hours)
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


def _day_boundary_positions(upcoming: list[dict[str, Any]]) -> list[float]:
    """Percentage x-positions (matching the sparkline's own point spacing -
    `i / (n - 1) * 100`) at which the 48h window crosses into a new
    calendar day, so "today" and "tomorrow" can be visually separated on
    the trend instead of reading as one undifferentiated 48h block.
    """
    n = len(upcoming)
    positions = []
    prev_date: datetime.date | None = None
    for i, hour in enumerate(upcoming):
        try:
            dt = datetime.datetime.fromisoformat(hour.get("time", ""))
        except ValueError:
            continue
        if prev_date is not None and dt.date() != prev_date:
            positions.append((i / (n - 1)) * 100)
        prev_date = dt.date()
    return positions


def render_weather_sparklines(hourly_data: list[dict[str, Any]]) -> html.Div | None:
    """Next-48h temperature / rain-chance mini trend charts - fills the
    horizontal space between current conditions and tomorrow's preview in
    the summary row with something more useful than empty space.
    """
    upcoming = _next_hours(hourly_data)
    if len(upcoming) < 2:
        return None

    temps = [h.get("temp_c", 0) for h in upcoming]
    rain = [h.get("rain_chance", 0) for h in upcoming]
    day_markers = _day_boundary_positions(upcoming)

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        "Next 48h",
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
                    "marginBottom": "0.25rem",
                },
            ),
            sparkline(
                temps,
                color=COLORS["gold"],
                height="1.9rem",
                day_markers=day_markers,
            ),
            # Rain chance is always 0-100%, scaled to that fixed range (not
            # its own min/max) so height is a true reading of "how much",
            # comparable across sparklines/refreshes.
            sparkline(
                rain,
                color=COLORS["accent"],
                height="0.9rem",
                fixed_range=(0, 100),
                day_markers=day_markers,
            ),
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
