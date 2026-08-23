from dash import html

from utils.styles import COLORS, FONT_SIZES, WEIGHT, kicker_style, row_style

from .data import get_time_color_and_weight


def render_tfl_summary(
    arrivals_data: dict,
    line_status: dict,
    stop_disruptions: dict,
) -> html.Div:
    """Render TFL summary view with next 2 departures and status indicators."""
    arrivals = arrivals_data.get("arrivals", [])
    station_name = arrivals_data.get("station_name", "")
    line_ids = arrivals_data.get("line_ids") or list(line_status.keys())

    next_arrivals = arrivals[:2]

    status_row = _create_status_row(
        line_ids,
        line_status,
        stop_disruptions,
        station_name,
    )

    children: list[html.Div] = [html.Div("Transport", style=kicker_style())]
    if status_row is not None:
        children.append(status_row)

    if next_arrivals:
        children.append(
            html.Div(
                [_create_arrival_row(a) for a in next_arrivals],
                style={"display": "flex", "flexDirection": "column"},
            ),
        )
    else:
        children.append(
            html.Div(
                "No transport arrivals",
                style={
                    "fontSize": FONT_SIZES["primary"],
                    "color": COLORS["text_muted"],
                    "padding": "0.4rem 0",
                },
            ),
        )

    return html.Div(
        children,
        style={
            "color": COLORS["text"],
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.3rem",
        },
    )


def _status_dot(color: str) -> html.Div:
    return html.Div(
        style={
            "width": "0.45rem",
            "height": "0.45rem",
            "borderRadius": "50%",
            "background": color,
            "flexShrink": 0,
        },
    )


def _create_status_row(
    line_ids: list,
    line_status: dict,
    stop_disruptions: dict,
    station_name: str,
) -> html.Div | None:
    """A single wrapped row of small dot+label status chips, instead of a
    stacked list - keeps this glanceable and compact.
    """
    indicators = []

    seen = set()
    resolved_line_ids = line_ids or list(line_status.keys())
    for line_id in resolved_line_ids:
        status = line_status.get(line_id)
        if status and line_id not in seen:
            status_color = {
                "green": COLORS["accent"],
                "yellow": COLORS["gold"],
                "red": COLORS["urgent"],
            }.get(status["status_color"], COLORS["text_secondary"])
            indicators.append(
                html.Div(
                    [
                        _status_dot(status_color),
                        html.Span(
                            status["line_name"],
                            style={
                                "fontSize": FONT_SIZES["small"],
                                "color": COLORS["text_secondary"],
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "0.3rem"},
                ),
            )
            seen.add(line_id)

    if stop_disruptions:
        indicators.append(
            html.Div(
                [
                    _status_dot(COLORS["gold"]),
                    html.Span(
                        f"{station_name} disruptions",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["text_secondary"],
                        },
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "gap": "0.3rem"},
            ),
        )

    if not indicators:
        return None

    return html.Div(
        indicators,
        style={"display": "flex", "flexWrap": "wrap", "gap": "0.2rem 0.9rem"},
    )


def _create_arrival_row(arrival: dict) -> html.Div:
    """A single arrival: line, destination, time - no card, a left accent
    bar only when the arrival is imminent (<2 min).
    """
    time_color, time_weight = get_time_color_and_weight(arrival["minutes"])
    line_color = arrival.get("line_color") or COLORS["accent"]
    transfer_indicator = arrival.get("transfer_station_indicator")

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        arrival["line_name"],
                        style={
                            "color": line_color,
                            "fontWeight": WEIGHT["semibold"],
                            "fontSize": FONT_SIZES["primary"],
                            "marginRight": "0.5rem",
                        },
                    ),
                    html.Span(
                        f"→ {arrival['destination']}",
                        style={
                            "color": COLORS["text"],
                            "fontSize": FONT_SIZES["primary"],
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "whiteSpace": "nowrap",
                        },
                    ),
                    html.Div(
                        transfer_indicator,
                        style={"marginLeft": "0.4rem", "flexShrink": 0},
                    )
                    if transfer_indicator
                    else None,
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "flex": "1",
                    "minWidth": "0",
                },
            ),
            html.Span(
                f"{arrival['minutes']}m" if arrival["minutes"] > 0 else "Due",
                style={
                    "color": time_color,
                    "fontSize": FONT_SIZES["heading"],
                    "fontWeight": time_weight,
                },
            ),
        ],
        style=row_style(
            divider=True,
            display="flex",
            alignItems="center",
            justifyContent="space-between",
            gap="0.5rem",
            borderLeft=f"2px solid {COLORS['urgent']}"
            if arrival["minutes"] < 2
            else "2px solid transparent",
        ),
    )
