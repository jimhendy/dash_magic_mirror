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
    """One index per line, stacked in the top-right corner. The return
    (this week's % change) is the point of a glance-level summary, so it's
    the bold, colored figure; the current price is dropped entirely here in
    favor of the full-screen view, which has room for it.
    """
    if not markets:
        return html.Div(
            "No market data available",
            style={"color": COLORS["text_muted"], "fontSize": FONT_SIZES["meta"]},
        )

    return html.Div(
        [_market_chip(m) for m in markets],
        style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "flex-end",
            "gap": "0.35rem",
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
                style={"width": "1.2rem", "height": "1.2rem", "flexShrink": 0},
            ),
            html.Div(
                style={"width": "3.6rem", "height": "1.4rem", "flexShrink": 0},
                # Split the trend at the week's opening level: the stretch
                # above it reads teal (gain), the stretch below red (loss),
                # so an intraday dip on an up week still shows as a dip.
                children=sparkline(
                    values,
                    color=COLORS["accent"],
                    baseline_color=COLORS["urgent"],
                    baseline=values[0],
                    height="1.4rem",
                ),
            ),
            html.Span(
                f"{'+' if is_up else ''}{pct:.1f}%",
                style={
                    "fontSize": FONT_SIZES["secondary"],
                    "fontWeight": WEIGHT["bold"],
                    "color": color,
                    "fontVariantNumeric": "tabular-nums",
                    "minWidth": "3.6rem",
                    "textAlign": "right",
                },
            ),
        ],
        style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
    )
