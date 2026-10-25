from typing import Any

from dash import html

from utils.sparkline import sparkline
from utils.styles import COLORS
from utils.ui import icon

from .constants import SUMMARY_DAYS
from .data import change_pct, summary_series


def trend_color(pct: float) -> str:
    return COLORS["accent"] if pct >= 0 else COLORS["urgent"]


def change_label(pct: float) -> str:
    arrow = "▲" if pct >= 0 else "▼"
    return f"{arrow} {abs(pct):.2f}%"


def render_markets_summary(markets: list[dict[str, Any]]) -> html.Div:
    """One row per index: its flag, last week's trend and today's move.
    Names and levels are on the panel."""
    rows = []
    for market in markets:
        series = summary_series(market, SUMMARY_DAYS)
        values = [pt["close"] for pt in series] or [market["price"]]
        week_pct = change_pct(series)
        day_pct = market["day_change_pct"]
        rows.append(
            html.Div(
                [
                    icon(market.get("icon", "mdi:chart-line"), "mkt__flag"),
                    sparkline(
                        values,
                        color=trend_color(week_pct),
                        class_name="mkt__spark",
                        baseline=values[0],
                    ),
                    html.Div(
                        change_label(day_pct),
                        className="mkt__change "
                        + ("is-up" if day_pct >= 0 else "is-down"),
                    ),
                ],
                className="mkt",
            ),
        )
    return html.Div(rows, className="mkts")
