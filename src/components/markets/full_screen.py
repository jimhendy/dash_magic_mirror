from typing import Any

from dash import html

from utils.sparkline import sparkline
from utils.ui import empty_state, icon, stat

from .constants import CHART_RANGE
from .data import change_pct
from .format import format_price, format_volume
from .summary import change_label, trend_color


def render_markets_fullscreen(markets: list[dict[str, Any]]) -> html.Div:
    if not markets:
        return html.Div(
            empty_state("No market data available", "mdi:chart-line"),
            className="detail",
        )
    return html.Div(
        html.Div([_market_card(m) for m in markets], className="mkt-grid"),
        className="detail",
    )


def _market_card(market: dict[str, Any]) -> html.Div:
    series = market.get("series") or []
    values = [pt["close"] for pt in series] or [market["price"]]
    day_pct = market["day_change_pct"]
    period_pct = change_pct(series)
    start_label = series[0]["time"].strftime("%d %b") if series else ""
    end_label = series[-1]["time"].strftime("%d %b") if series else ""
    currency = market["currency"]

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    icon(
                                        market.get("icon", "mdi:chart-line"),
                                        "mkt-card__flag",
                                    ),
                                    market["label"],
                                ],
                                className="mkt-card__label",
                            ),
                            html.Div(
                                format_price(market["price"], currency),
                                className="mkt-card__price",
                            ),
                        ],
                    ),
                    html.Div(
                        [
                            html.Div(
                                change_label(day_pct),
                                className="mkt__change mkt__change--lg "
                                + ("is-up" if day_pct >= 0 else "is-down"),
                            ),
                            html.Div("today", className="mkt-card__caption"),
                        ],
                        className="mkt-card__day",
                    ),
                ],
                className="mkt-card__head",
            ),
            html.Div(
                [
                    sparkline(
                        values,
                        color=trend_color(period_pct),
                        class_name="mkt-card__chart",
                        baseline=values[0],
                        stroke=2.5,
                    ),
                    html.Div(
                        [
                            html.Span(start_label),
                            html.Span(
                                f"{CHART_RANGE} {'+' if period_pct >= 0 else ''}{period_pct:.1f}%",
                                className="is-up" if period_pct >= 0 else "is-down",
                            ),
                            html.Span(end_label),
                        ],
                        className="mkt-card__axis",
                    ),
                ],
            ),
            _range_bar(market),
            html.Div(
                [
                    stat("Day high", format_price(market.get("day_high"), currency)),
                    stat("Day low", format_price(market.get("day_low"), currency)),
                    stat("Volume", format_volume(market.get("volume"))),
                ],
                className="stat-grid stat-grid--3",
            ),
        ],
        className="card mkt-card",
    )


def _range_bar(market: dict[str, Any]) -> html.Div | None:
    lo, hi = market.get("fifty_two_week_low"), market.get("fifty_two_week_high")
    if lo is None or hi is None or hi <= lo:
        return None
    pct = max(0.0, min(100.0, (market["price"] - lo) / (hi - lo) * 100))
    currency = market["currency"]
    return html.Div(
        [
            html.Div("52-week range", className="stat__label"),
            html.Div(
                html.Div(className="range__marker", style={"left": f"{pct:.1f}%"}),
                className="range range--wide",
            ),
            html.Div(
                [
                    html.Span(format_price(lo, currency)),
                    html.Span(format_price(hi, currency)),
                ],
                className="mkt-card__axis",
            ),
        ],
        className="mkt-card__range",
    )
