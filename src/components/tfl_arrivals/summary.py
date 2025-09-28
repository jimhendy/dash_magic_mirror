from dash import html

from utils.styles import COLORS, FONT_SIZES, TEXT_STYLES

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

    # Get next 2 arrivals
    next_arrivals = arrivals[:2]

    # Create status indicators
    status_indicators = _create_status_indicators(
        line_ids,
        line_status,
        stop_disruptions,
        station_name,
    )
    has_status = bool(status_indicators.children)

    # Create arrival cards
    arrival_cards = []
    for arrival in next_arrivals:
        arrival_card = _create_arrival_card(arrival)
        arrival_cards.append(arrival_card)

    children: list[html.Div] = []
    if has_status:
        children.append(status_indicators)

    if arrival_cards:
        children.append(
            html.Div(
                arrival_cards,
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "8px",
                    "marginTop": "12px" if has_status else "0px",
                },
            ),
        )
    else:
        children.append(
            html.Div(
                "No transport arrivals",
                style={
                    "fontSize": FONT_SIZES["summary_primary"],
                    "color": COLORS["soft_gray"],
                    "textAlign": "center",
                    "padding": "1.5rem 1rem 0.5rem 1rem",
                },
            ),
        )

    return html.Div(
        children,
        style={
            "color": COLORS["white"],
        },
    )


def _create_status_indicators(
    line_ids: list,
    line_status: dict,
    stop_disruptions: dict,
    station_name: str,
) -> html.Div:
    """Create status indicators for lines and station."""
    indicators = []

    # Line status indicators
    seen = set()
    resolved_line_ids = line_ids or list(line_status.keys())
    for line_id in resolved_line_ids:
        status = line_status.get(line_id)
        if status and line_id not in seen:
            indicator = _create_line_status_indicator(status)
            indicators.append(indicator)
            seen.add(line_id)

    # Station disruption indicators
    if stop_disruptions:
        station_indicator = _create_station_disruption_indicator(station_name)
        indicators.append(station_indicator)

    if not indicators:
        return html.Div()

    return html.Div(
        indicators,
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "4px",
            "marginBottom": "8px",
        },
    )


def _create_line_status_indicator(status: dict) -> html.Div:
    """Create a line status indicator."""
    status_color = {
        "green": COLORS["green"],
        "yellow": COLORS["gold"],
        "red": COLORS["red"],
    }.get(status["status_color"], COLORS["soft_gray"])

    return html.Div(
        [
            html.Span(
                "●",
                style={
                    "color": status_color,
                    "marginRight": "8px",
                    "fontSize": FONT_SIZES["summary_secondary"],
                },
            ),
            html.Span(
                status["line_name"],
                style=TEXT_STYLES["secondary"]
                | {
                    "color": COLORS["white"],
                    "marginRight": "6px",
                },
            ),
            html.Span(
                status["status_text"],
                style=TEXT_STYLES["secondary"] | {"color": status_color},
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "fontSize": FONT_SIZES["summary_secondary"],
        },
    )


def _create_station_disruption_indicator(station_name: str) -> html.Div:
    """Create a station disruption indicator."""
    return html.Div(
        [
            html.Span(
                "⚠",
                style={
                    "color": COLORS["gold"],
                    "marginRight": "8px",
                    "fontSize": FONT_SIZES["summary_secondary"],
                },
            ),
            html.Span(
                f"{station_name} has disruptions",
                style=TEXT_STYLES["secondary"] | {"color": COLORS["white"]},
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "fontSize": FONT_SIZES["summary_secondary"],
        },
    )


def _create_arrival_card(arrival: dict) -> html.Div:
    """Create an arrival card for summary view."""
    time_color, time_weight = get_time_color_and_weight(arrival["minutes"])
    line_color = arrival.get("line_color") or COLORS["blue"]

    return html.Div(
        [
            html.Div(
                [
                    # Left side: Line and destination info
                    html.Div(
                        [
                            html.Span(
                                arrival["line_name"],
                                style={
                                    "color": line_color,
                                    "fontWeight": "600",
                                    "fontSize": FONT_SIZES["summary_primary"],
                                    "marginRight": "8px",
                                },
                            ),
                            html.Span(
                                f"→ {arrival['destination']}",
                                style={
                                    "color": COLORS["white"],
                                    "fontSize": FONT_SIZES["summary_primary"],
                                    "fontWeight": "400",
                                    "flex": "1",
                                },
                            ),
                            # Transfer station indicator
                            html.Span(
                                arrival.get("transfer_station_indicator", ""),
                                style={
                                    "fontSize": FONT_SIZES["summary_primary"],
                                    "marginLeft": "8px",
                                    "color": COLORS["green"]
                                    if arrival.get("transfer_station_indicator")
                                    else "transparent",
                                    "fontWeight": "700",
                                    "marginRight": "auto",
                                    "title": "Stops at Transfer Station"
                                    if arrival.get("transfer_station_indicator")
                                    else "",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "flex": "1",
                        },
                    ),
                    # Right side: Time
                    html.Div(
                        [
                            html.Span(
                                f"{arrival['minutes']}m"
                                if arrival["minutes"] > 0
                                else "Due",
                                style={
                                    "color": time_color,
                                    "fontSize": FONT_SIZES["summary_heading"],
                                    "fontWeight": time_weight,
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "whiteSpace": "nowrap",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "width": "100%",
                    "gap": "8px",
                },
            ),
        ],
        style={
            "background": "linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
            "border": "1px solid rgba(255,255,255,0.08)",
            "borderRadius": "8px",
            "padding": "12px 16px",
            "marginBottom": "0",
            "backdropFilter": "blur(10px)",
        },
    )
