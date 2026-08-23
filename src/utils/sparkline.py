"""Reusable pure-CSS sparklines (`clip-path: polygon(...)` divs) - no SVG or
charting library needed for a small decorative trend indicator. Dash's
`html` module has no SVG primitives, and percentages in `clip-path` are
relative to the element's own box, so this stays fully responsive to
whatever width/height it's given. Used by both the weather and markets
components.

Each sparkline layers two clipped shapes: a translucent area fill (context)
under a solid, full-opacity "ribbon" tracing the actual line (the part that
needs to read clearly from across a room) - a gradient fill alone reads as
too faint at a glance.
"""

from __future__ import annotations

from dash import html

_LINE_THICKNESS = 5.0  # % of the sparkline's own height
_DAY_MARKER_COLOR = "rgba(255, 255, 255, 0.14)"


def _scale(
    values: list[float],
    *,
    fixed_range: tuple[float, float] | None,
    pad: float,
) -> tuple[float, float]:
    if fixed_range is not None:
        return fixed_range
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    # Pad the range so the trend doesn't touch the very top/bottom edge.
    return lo - span * pad, hi + span * pad


def _points(values: list[float], lo: float, hi: float) -> list[tuple[float, float]]:
    span = (hi - lo) or 1.0
    n = len(values)
    if n == 1:
        return [(0.0, 100 - ((values[0] - lo) / span) * 100)]
    return [
        ((i / (n - 1)) * 100, 100 - ((v - lo) / span) * 100)
        for i, v in enumerate(values)
    ]


def area_polygon(
    values: list[float],
    *,
    fixed_range: tuple[float, float] | None = None,
    pad: float = 0.15,
) -> str:
    """A `clip-path: polygon(...)` string tracing a filled area under `values`.

    With `fixed_range` (e.g. `(0, 100)` for a percentage), values are scaled
    against that fixed scale instead of their own min/max - important for a
    value where the *absolute* level matters (e.g. rain chance: a quiet day
    at 1-5% shouldn't look as dramatic as a wet one just because it's
    auto-scaled to fill the same box).
    """
    lo, hi = _scale(values, fixed_range=fixed_range, pad=pad)
    pts = [f"{x:.2f}% {y:.2f}%" for x, y in _points(values, lo, hi)]
    return "polygon(0% 100%, " + ", ".join(pts) + ", 100% 100%)"


def line_polygon(
    values: list[float],
    *,
    fixed_range: tuple[float, float] | None = None,
    pad: float = 0.15,
    thickness: float = _LINE_THICKNESS,
) -> str:
    """A thin solid "ribbon" tracing the line itself - a `clip-path` has no
    stroke, so this fakes one: a band of fixed thickness around each point,
    filled at full opacity, drawn on top of the (translucent) area fill.
    """
    lo, hi = _scale(values, fixed_range=fixed_range, pad=pad)
    points = _points(values, lo, hi)
    half = thickness / 2
    top = [(x, max(0.0, y - half)) for x, y in points]
    bottom = [(x, min(100.0, y + half)) for x, y in points]
    pts = [f"{x:.2f}% {y:.2f}%" for x, y in top] + [
        f"{x:.2f}% {y:.2f}%" for x, y in reversed(bottom)
    ]
    return "polygon(" + ", ".join(pts) + ")"


def sparkline(
    values: list[float],
    *,
    color: str,
    height: str,
    fixed_range: tuple[float, float] | None = None,
    day_markers: list[float] | None = None,
) -> html.Div:
    """A two-layer sparkline: soft area fill + solid line, both from `values`.

    `day_markers` is an optional list of x-positions (percent, 0-100,
    matching this sparkline's own point spacing) at which to draw a thin
    vertical divider behind the trend - used by the weather sparklines to
    mark where one calendar day ends and the next begins across the 48h
    window.
    """
    children = [
        html.Div(
            style={
                "position": "absolute",
                "top": "0",
                "bottom": "0",
                "left": f"{pct:.2f}%",
                "width": "1px",
                "background": _DAY_MARKER_COLOR,
            },
        )
        for pct in (day_markers or [])
    ]
    children.extend(
        [
            html.Div(
                style={
                    "position": "absolute",
                    "inset": "0",
                    "background": f"linear-gradient(180deg, {color}80 0%, {color}1f 100%)",
                    "clipPath": area_polygon(values, fixed_range=fixed_range),
                },
            ),
            html.Div(
                style={
                    "position": "absolute",
                    "inset": "0",
                    "background": color,
                    "clipPath": line_polygon(values, fixed_range=fixed_range),
                },
            ),
        ],
    )
    return html.Div(
        children,
        style={"position": "relative", "height": height, "width": "100%"},
    )
