from typing import Any

from dash import html

from utils.sparkline import sparkline
from utils.styles import COLORS, FONT_SIZES, WEIGHT, kicker_style, row_style

from .constants import SUMMARY_DAYS
from .data import change_pct, summary_series
from .format import format_price


def render_markets_summary(markets: list[dict[str, Any]]) -> html.Div:
    """Kicker label + one row per index: name, price, week change, a small
    sparkline of the last week or so - matching the weather sparklines.
    """
    if not markets:
        return html.Div(
            [
                html.Div("Markets", style=kicker_style()),
                html.Div(
                    "No market data available",
                    style={
                        "color": COLORS["text_muted"],
                        "fontSize": FONT_SIZES["primary"],
                    },
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "0.4rem"},
        )

    rows = [_market_row(m) for m in markets]
    return html.Div(
        [html.Div("Markets", style=kicker_style()), *rows],
        style={"display": "flex", "flexDirection": "column"},
    )


def _market_row(market: dict[str, Any]) -> html.Div:
    series = summary_series(market, SUMMARY_DAYS)
    pct = change_pct(series)
    is_up = pct >= 0
    change_color = COLORS["accent"] if is_up else COLORS["urgent"]
    values = [pt["close"] for pt in series] or [market["price"]]

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        market["label"],
                        style={
                            "fontSize": FONT_SIZES["primary"],
                            "fontWeight": WEIGHT["semibold"],
                            "color": COLORS["text"],
                        },
                    ),
                    html.Span(
                        format_price(market["price"], market["currency"]),
                        style={
                            "fontSize": FONT_SIZES["secondary"],
                            "color": COLORS["text_secondary"],
                            "marginLeft": "0.6rem",
                        },
                    ),
                ],
                style={"flex": "1", "minWidth": "0"},
            ),
            html.Div(
                style={"width": "6rem", "margin": "0 1rem", "flexShrink": 0},
                children=sparkline(values, color=change_color, height="1.6rem"),
            ),
            html.Span(
                f"{'+' if is_up else ''}{pct:.1f}%",
                style={
                    "fontSize": FONT_SIZES["secondary"],
                    "fontWeight": WEIGHT["bold"],
                    "color": change_color,
                    "minWidth": "3.5rem",
                    "textAlign": "right",
                },
            ),
        ],
        style=row_style(divider=True, display="flex", alignItems="center"),
    )
