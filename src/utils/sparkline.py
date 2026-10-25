"""Tiny SVG sparklines, served as `data:` URIs in an `<img>`.

Dash's `html` module has no SVG elements, but an `<img>` pointing at an
inline SVG gets a crisp, resolution-independent vector line for free.
`preserveAspectRatio="none"` stretches it to whatever box CSS gives it and
`vector-effect: non-scaling-stroke` keeps the stroke width constant while
it stretches, so one helper serves both the small tile sparklines and the
large detail charts.
"""

from __future__ import annotations

from urllib.parse import quote

from dash import html

_W = 100.0
_H = 40.0


def _scale(values: list[float], fixed_range: tuple[float, float] | None, pad: float):
    if fixed_range is not None:
        return fixed_range
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    return lo - span * pad, hi + span * pad


def sparkline_svg(
    values: list[float],
    *,
    color: str,
    fixed_range: tuple[float, float] | None = None,
    baseline: float | None = None,
    stroke: float = 2.0,
    fill: bool = True,
    pad: float = 0.12,
) -> str:
    """Return the raw SVG markup for a sparkline of `values`."""
    if not values:
        values = [0.0]
    if len(values) == 1:
        values = values * 2
    lo, hi = _scale(values, fixed_range, pad)
    span = (hi - lo) or 1.0
    n = len(values)

    def y(v: float) -> float:
        return _H - ((v - lo) / span) * _H

    pts = [(i / (n - 1) * _W, y(v)) for i, v in enumerate(values)]
    line = " ".join(f"{x:.2f},{yy:.2f}" for x, yy in pts)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W:g} {_H:g}" '
        'preserveAspectRatio="none">',
        "<defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'>"
        f"<stop offset='0' stop-color='{color}' stop-opacity='0.35'/>"
        f"<stop offset='1' stop-color='{color}' stop-opacity='0'/>"
        "</linearGradient></defs>",
    ]
    if fill:
        area = f"0,{_H} {line} {_W:g},{_H}"
        parts.append(f"<polygon points='{area}' fill='url(#g)'/>")
    if baseline is not None and lo <= baseline <= hi:
        by = y(baseline)
        parts.append(
            f"<line x1='0' y1='{by:.2f}' x2='{_W:g}' y2='{by:.2f}' "
            "stroke='white' stroke-opacity='0.18' stroke-dasharray='2 2' "
            "vector-effect='non-scaling-stroke' stroke-width='1'/>",
        )
    parts.append(
        f"<polyline points='{line}' fill='none' stroke='{color}' "
        f"stroke-width='{stroke}' stroke-linejoin='round' stroke-linecap='round' "
        "vector-effect='non-scaling-stroke'/>",
    )
    parts.append("</svg>")
    return "".join(parts)


def sparkline(
    values: list[float],
    *,
    color: str,
    class_name: str = "spark",
    **kwargs,
) -> html.Img:
    """An `<img>` rendering `values` as a sparkline; size it with CSS."""
    svg = sparkline_svg(values, color=color, **kwargs)
    return html.Img(
        src="data:image/svg+xml;charset=utf-8," + quote(svg),
        className=class_name,
        alt="",
    )
