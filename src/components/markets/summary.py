from typing import Any

from dash import html
from dash_iconify import DashIconify

from utils.sparkline import sparkline
from utils.styles import COLORS, FONT_SIZES, WEIGHT

from .constants import SUMMARY_DAYS
from .data import change_pct, summary_series

# Circular national flags (from the "circle-flags" Iconify set) stand in
# for the index name - a globe for ACWI, since it's a global index rather
# than a single country's.
_SYMBOL_ICONS = {
    "^GSPC": "circle-flags:us",
    "^FTSE": "circle-flags:gb",
    "ACWI": "mdi:earth",
}


def render_markets_summary(markets: list[dict[str, Any]]) -> html.Div:
    """Kicker label + all indices spread evenly across one line. The
    return (this week's % change) is the point of a glance-level summary,
    so it's the large, bold, colored figure; the current price is dropped
    entirely here in favor of the full-screen view, which has room for it.
    """
    if not markets:
        return html.Div(
            "No market data available",
            style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["primary"]},
        )

    chips = [_market_chip(m) for m in markets]
    return html.Div(
        chips,
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
        },
    )


def _market_chip(market: dict[str, Any]) -> html.Div:
    series = summary_series(market, SUMMARY_DAYS)
    pct = change_pct(series)
    is_up = pct >= 0
    color = COLORS["accent"] if is_up else COLORS["urgent"]
    values = [pt["close"] for pt in series] or [market["price"]]

    return html.Div(
        [
            DashIconify(
                icon=_SYMBOL_ICONS.get(market["symbol"], "mdi:chart-line"),
                color=COLORS["text_muted"],
                style={"width": "1.3rem", "height": "1.3rem", "flexShrink": 0},
            ),
            html.Div(
                style={"width": "4.5rem", "height": "1.6rem", "flexShrink": 0},
                children=sparkline(values, color=color, height="1.6rem"),
            ),
            html.Span(
                f"{'+' if is_up else ''}{pct:.1f}%",
                style={
                    "fontSize": FONT_SIZES["heading"],
                    "fontWeight": WEIGHT["bold"],
                    "color": color,
                },
            ),
        ],
        style={"display": "flex", "alignItems": "center", "gap": "0.6rem"},
    )
