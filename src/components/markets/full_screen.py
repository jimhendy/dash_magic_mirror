from typing import Any

from dash import html

from utils.sparkline import sparkline
from utils.styles import COLORS, FONT_SIZES, SPACE, WEIGHT, kicker_style, panel_style

from .constants import CHART_RANGE
from .data import change_pct
from .format import format_price, format_volume


def render_markets_fullscreen(markets: list[dict[str, Any]]) -> html.Div:
    """One detailed card per index: price, day change, a full-range chart,
    a 52-week range indicator, and day high/low/volume - the "much more"
    version of the summary row.
    """
    if not markets:
        return html.Div(
            "No market data available",
            style={
                "color": COLORS["text_muted"],
                "textAlign": "center",
                "padding": SPACE["xl"],
            },
        )

    return html.Div(
        [_market_card(m) for m in markets],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": SPACE["xl"],
            "padding": SPACE["xl"],
        },
    )


def _market_card(market: dict[str, Any]) -> html.Div:
    series = market.get("series") or []
    values = [pt["close"] for pt in series] or [market["price"]]
    day_pct = market["day_change_pct"]
    day_up = day_pct >= 0
    day_color = COLORS["accent"] if day_up else COLORS["urgent"]

    period_pct = change_pct(series)
    period_up = period_pct >= 0
    period_color = COLORS["accent"] if period_up else COLORS["urgent"]

    start_label = series[0]["time"].strftime("%d %b") if series else ""
    end_label = series[-1]["time"].strftime("%d %b") if series else ""

    return html.Div(
        [
            # Header: name, price, day change
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(market["label"], style=kicker_style()),
                            html.Span(
                                format_price(market["price"], market["currency"]),
                                style={
                                    "fontSize": FONT_SIZES["heading"],
                                    "fontWeight": WEIGHT["semibold"],
                                    "color": COLORS["text"],
                                },
                            ),
                        ],
                    ),
                    html.Div(
                        [
                            html.Span(
                                f"{'+' if day_up else ''}{day_pct:.2f}%",
                                style={
                                    "fontSize": FONT_SIZES["primary"],
                                    "fontWeight": WEIGHT["bold"],
                                    "color": day_color,
                                },
                            ),
                            html.Div(
                                "today",
                                style={
                                    "fontSize": FONT_SIZES["small"],
                                    "color": COLORS["text_muted"],
                                },
                            ),
                        ],
                        style={"textAlign": "right"},
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "flex-end",
                },
            ),
            # Chart: full CHART_RANGE, bigger than the summary sparkline
            html.Div(
                sparkline(values, color=period_color, height="6rem"),
                style={"margin": f"{SPACE['md']} 0"},
            ),
            html.Div(
                [
                    html.Span(start_label, style={"color": COLORS["text_muted"]}),
                    html.Span(
                        f"{CHART_RANGE} change: {'+' if period_up else ''}{period_pct:.1f}%",
                        style={"color": period_color, "fontWeight": WEIGHT["semibold"]},
                    ),
                    html.Span(end_label, style={"color": COLORS["text_muted"]}),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "fontSize": FONT_SIZES["small"],
                    "marginBottom": SPACE["lg"],
                },
            ),
            # 52-week range
            _range_bar(market),
            # Day high/low + volume
            html.Div(
                [
                    _stat(
                        "Day low", format_price(market["day_low"], market["currency"])
                    ),
                    _stat(
                        "Day high", format_price(market["day_high"], market["currency"])
                    ),
                    _stat("Volume", format_volume(market["volume"])),
                ],
                style={"display": "flex", "gap": SPACE["xl"], "marginTop": SPACE["lg"]},
            ),
        ],
        style=panel_style(padding=SPACE["xl"]),
    )


def _stat(label: str, value: str) -> html.Div:
    return html.Div(
        [
            html.Div(
                label,
                style={
                    "fontSize": FONT_SIZES["small"],
                    "color": COLORS["text_muted"],
                    "textTransform": "uppercase",
                    "letterSpacing": "0.06em",
                },
            ),
            html.Div(
                value,
                style={
                    "fontSize": FONT_SIZES["secondary"],
                    "color": COLORS["text"],
                    "fontWeight": WEIGHT["semibold"],
                },
            ),
        ],
    )


def _range_bar(market: dict[str, Any]) -> html.Div:
    """Where the current price sits within its 52-week range."""
    lo, hi, price = (
        market.get("fifty_two_week_low"),
        market.get("fifty_two_week_high"),
        market.get("price"),
    )
    if lo is None or hi is None or price is None or hi <= lo:
        return html.Div()

    pct = max(0.0, min(100.0, (price - lo) / (hi - lo) * 100))
    currency = market["currency"]

    return html.Div(
        [
            html.Div(
                [
                    html.Span("52-week low", style={"color": COLORS["text_muted"]}),
                    html.Span("52-week high", style={"color": COLORS["text_muted"]}),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "fontSize": FONT_SIZES["small"],
                    "marginBottom": "0.3rem",
                },
            ),
            html.Div(
                html.Div(
                    style={
                        "position": "absolute",
                        "left": f"{pct}%",
                        "top": "-0.2rem",
                        "width": "0.6rem",
                        "height": "0.6rem",
                        "borderRadius": "50%",
                        "background": COLORS["accent"],
                        "transform": "translateX(-50%)",
                        "boxShadow": f"0 0 0 3px {COLORS['bg']}",
                    },
                ),
                style={
                    "position": "relative",
                    "height": "0.2rem",
                    "background": COLORS["hairline_strong"],
                    "borderRadius": "999px",
                },
            ),
            html.Div(
                [
                    html.Span(
                        format_price(lo, currency),
                        style={"color": COLORS["text_secondary"]},
                    ),
                    html.Span(
                        format_price(hi, currency),
                        style={"color": COLORS["text_secondary"]},
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "fontSize": FONT_SIZES["small"],
                    "marginTop": "0.3rem",
                },
            ),
        ],
        style={"marginTop": SPACE["sm"]},
    )
