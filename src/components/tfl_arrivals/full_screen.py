from dash import html

from utils.styles import COLORS

from .data import get_time_color_and_weight


def render_tfl_fullscreen(
    all_arrivals_data: dict, line_status: dict, stop_disruptions: dict,
) -> html.Div:
    """Render TFL full screen view with all arrivals and status tables."""
    # Combine all arrivals from all stops
    all_arrivals = []
    all_line_ids = set()
    all_stop_ids = set()

    for stop_id, data in all_arrivals_data.items():
        arrivals = data.get("arrivals", [])
        line_ids = data.get("line_ids", [])
        all_arrivals.extend(arrivals)
        all_line_ids.update(line_ids)
        all_stop_ids.add(stop_id)

    # Sort all arrivals by time
    all_arrivals.sort(key=lambda x: x["minutes"])

    # Limit to what fits on screen (approximately 20-25 entries)
    display_arrivals = all_arrivals[:25]

    return html.Div(
        [
            # Status tables section (top row)
            html.Div(
                [
                    # Line status table
                    html.Div(
                        [
                            html.H3(
                                "Line Status",
                                style={
                                    "fontSize": "1.5rem",
                                    "fontWeight": "500",
                                    "color": COLORS["blue"],
                                    "marginBottom": "15px",
                                    "textAlign": "center",
                                },
                            ),
                            _create_line_status_table(all_line_ids, line_status),
                        ],
                        style={
                            "flex": "1",
                            "marginRight": "20px",
                        },
                    ),
                    # Station disruptions table
                    html.Div(
                        [
                            html.H3(
                                "Station Status",
                                style={
                                    "fontSize": "1.5rem",
                                    "fontWeight": "500",
                                    "color": COLORS["blue"],
                                    "marginBottom": "15px",
                                    "textAlign": "center",
                                },
                            ),
                            _create_station_status_table(
                                all_stop_ids, stop_disruptions, all_arrivals_data,
                            ),
                        ],
                        style={
                            "flex": "1",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "marginBottom": "40px",
                },
            ),
            # Arrivals table section (full width below status tables)
            html.Div(
                [
                    _create_arrivals_table(display_arrivals),
                ],
                style={
                    "width": "100%",
                },
            ),
        ],
        style={
            "padding": "20px",
            "color": COLORS["white"],
            "fontFamily": "'Inter', 'Roboto', 'Segoe UI', 'Helvetica Neue', sans-serif",
        },
    )


def _create_arrivals_table(arrivals: list) -> html.Div:
    """Create the arrivals table for full screen view."""
    if not arrivals:
        return html.Div(
            "No arrivals available",
            style={
                "textAlign": "center",
                "color": COLORS["soft_gray"],
                "fontSize": "1.2rem",
                "padding": "40px",
            },
        )

    # Table header
    header = html.Div(
        [
            html.Div("Station", style={"flex": "2", "fontWeight": "600"}),
            html.Div("Line", style={"flex": "1.5", "fontWeight": "600"}),
            html.Div("Destination", style={"flex": "2.5", "fontWeight": "600"}),
            html.Div("Platform", style={"flex": "1", "fontWeight": "600"}),
            html.Div("Time", style={"flex": "1", "fontWeight": "600"}),
            html.Div(
                "Expected",
                style={"flex": "1", "fontWeight": "600", "textAlign": "right"},
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "padding": "15px 20px",
            "borderBottom": f"2px solid {COLORS['blue']}",
            "fontSize": "1.1rem",
            "color": COLORS["blue"],
            "marginBottom": "10px",
        },
    )

    # Table rows
    rows = []
    for i, arrival in enumerate(arrivals):
        time_color, time_weight = get_time_color_and_weight(arrival["minutes"])

        # Alternate row colors
        bg_color = "rgba(255,255,255,0.03)" if i % 2 == 0 else "rgba(255,255,255,0.08)"

        # Clean platform display - replace "Platform null" or "null" with ""
        platform_text = arrival.get("platform", "")
        if platform_text in ["null", "Platform null", "Platform Unknown"]:
            platform_text = ""
        elif platform_text.startswith("Platform "):
            platform_text = platform_text.replace("Platform ", "")

        # Format the actual arrival time (e.g., "07:31")
        actual_time_text = ""
        if arrival.get("arrival_time"):
            # Convert to local time for display
            local_time = arrival["arrival_time"].astimezone()
            actual_time_text = local_time.strftime("%H:%M")

        row = html.Div(
            [
                html.Div(
                    arrival["station_name"],
                    style={
                        "flex": "2",
                        "color": COLORS["white"],
                        "fontSize": "1rem",
                    },
                ),
                html.Div(
                    arrival["line_name"],
                    style={
                        "flex": "1.5",
                        "color": COLORS["blue"],
                        "fontSize": "0.95rem",
                        "fontWeight": "500",
                    },
                ),
                html.Div(
                    arrival["destination"],
                    style={
                        "flex": "2.5",
                        "color": COLORS["white"],
                        "fontSize": "1rem",
                    },
                ),
                html.Div(
                    platform_text,
                    style={
                        "flex": "1",
                        "color": COLORS["soft_gray"],
                        "fontSize": "0.9rem",
                    },
                ),
                html.Div(
                    actual_time_text,
                    style={
                        "flex": "1",
                        "color": COLORS["white"],
                        "fontSize": "1rem",
                        "fontWeight": "400",
                    },
                ),
                html.Div(
                    f"{arrival['minutes']}m" if arrival["minutes"] > 0 else "Due",
                    style={
                        "flex": "1",
                        "color": time_color,
                        "fontSize": "1.1rem",
                        "fontWeight": time_weight,
                        "textAlign": "right",
                    },
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "padding": "12px 20px",
                "background": bg_color,
                "borderRadius": "6px",
                "marginBottom": "2px",
                "border": "1px solid rgba(255,255,255,0.05)",
            },
        )
        rows.append(row)

    return html.Div([header] + rows)


def _create_line_status_table(line_ids: set, line_status: dict) -> html.Div:
    """Create the line status table."""
    if not line_ids or not line_status:
        return html.Div(
            "No line status available",
            style={
                "textAlign": "center",
                "color": COLORS["soft_gray"],
                "fontSize": "1rem",
                "padding": "20px",
            },
        )

    rows = []
    for line_id in sorted(line_ids):
        if line_id in line_status:
            status = line_status[line_id]
            status_color = {
                "green": COLORS["green"],
                "yellow": COLORS["gold"],
                "red": COLORS["red"],
            }.get(status["status_color"], COLORS["soft_gray"])

            row = html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                "●",
                                style={
                                    "color": status_color,
                                    "marginRight": "10px",
                                    "fontSize": "1.2rem",
                                },
                            ),
                            html.Span(
                                status["line_name"],
                                style={
                                    "fontWeight": "500",
                                    "color": COLORS["white"],
                                },
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center", "flex": "1"},
                    ),
                    html.Div(
                        status["status_text"],
                        style={
                            "color": status_color,
                            "fontSize": "0.9rem",
                            "textAlign": "right",
                            "flex": "1",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "padding": "10px 15px",
                    "background": "rgba(255,255,255,0.05)",
                    "borderRadius": "6px",
                    "marginBottom": "5px",
                    "border": f"1px solid {status_color}33",
                },
            )
            rows.append(row)

    return html.Div(rows)


def _create_station_status_table(
    stop_ids: set, stop_disruptions: dict, all_arrivals_data: dict,
) -> html.Div:
    """Create the station status table."""
    if not stop_ids:
        return html.Div(
            "No stations configured",
            style={
                "textAlign": "center",
                "color": COLORS["soft_gray"],
                "fontSize": "1rem",
                "padding": "20px",
            },
        )

    rows = []
    has_disruptions = False

    for stop_id in sorted(stop_ids):
        # Get station name from arrivals data
        station_name = "Unknown Station"
        if stop_id in all_arrivals_data:
            station_name = all_arrivals_data[stop_id].get("station_name", stop_id)

        if stop_disruptions.get(stop_id):
            has_disruptions = True
            disruptions = stop_disruptions[stop_id]

            for disruption in disruptions:
                row = html.Div(
                    [
                        html.Div(
                            [
                                html.Span(
                                    "⚠",
                                    style={
                                        "color": COLORS["gold"],
                                        "marginRight": "10px",
                                        "fontSize": "1.2rem",
                                    },
                                ),
                                html.Span(
                                    station_name,
                                    style={
                                        "fontWeight": "500",
                                        "color": COLORS["white"],
                                        "fontSize": "0.9rem",
                                    },
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center"},
                        ),
                        html.Div(
                            disruption["description"][:50] + "..."
                            if len(disruption["description"]) > 50
                            else disruption["description"],
                            style={
                                "color": COLORS["soft_gray"],
                                "fontSize": "0.8rem",
                                "marginTop": "5px",
                            },
                        ),
                    ],
                    style={
                        "padding": "10px 15px",
                        "background": "rgba(255,193,61,0.1)",
                        "borderRadius": "6px",
                        "marginBottom": "5px",
                        "border": f"1px solid {COLORS['gold']}33",
                    },
                )
                rows.append(row)

    if not has_disruptions:
        return html.Div(
            [
                html.Div(
                    [
                        html.Span(
                            "✓",
                            style={
                                "color": COLORS["green"],
                                "marginRight": "10px",
                                "fontSize": "1.2rem",
                            },
                        ),
                        html.Span(
                            "All stations operating normally",
                            style={
                                "fontWeight": "500",
                                "color": COLORS["green"],
                                "fontSize": "0.9rem",
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center"},
                ),
            ],
            style={
                "padding": "15px",
                "background": "rgba(46,204,113,0.1)",
                "borderRadius": "6px",
                "border": f"1px solid {COLORS['green']}33",
                "textAlign": "center",
            },
        )

    return html.Div(rows)
