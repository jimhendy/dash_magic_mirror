# Explicit London timezone conversion (container may run in UTC)
from datetime import UTC

from dash import dcc, html
from dash_iconify import DashIconify

from utils.styles import COLORS, kicker_style, panel_style, row_style

from .data import get_time_color_and_weight

try:  # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore

    LONDON_TZ = ZoneInfo("Europe/London")
except Exception:  # pragma: no cover
    LONDON_TZ = None


def render_tfl_fullscreen(
    all_arrivals_data: dict,
    line_status: dict,
    stop_disruptions: dict,
    component_id: str,
) -> html.Div:
    """Render TFL full screen view with all arrivals and status tables plus a line filter."""
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

    # Limit to what fits on screen comfortably with the new layout
    display_arrivals = all_arrivals[:20]

    # Build unique line filter options (modeled after Sports)
    line_names = []
    seen = set()
    for a in all_arrivals:
        name = a.get("line_name") or ""
        if not name:
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            line_names.append(name)

    filter_options = [{"label": "All", "value": "all"}] + [
        {"label": name, "value": name.lower()} for name in line_names
    ]

    return html.Div(
        [
            # Sticky filter bar at the very top
            html.Div(
                [
                    dcc.RadioItems(
                        id=f"{component_id}-line-filter",
                        options=filter_options,
                        value="all",
                        inline=True,
                        labelStyle={
                            "marginRight": "0.75rem",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "0.25rem",
                        },
                        style={
                            "fontSize": "0.9rem",
                            "display": "flex",
                            "flexWrap": "wrap",
                            "gap": "1rem",
                            "color": COLORS["text"],
                            "marginBottom": "0.4rem",
                            "justifyContent": "center",
                            "width": "100%",
                        },
                    ),
                ],
                style={
                    "position": "sticky",
                    "top": "0",
                    "zIndex": 1,
                    "background": COLORS["bg"],
                    "padding": "0.5rem 0.6rem 0.25rem 0.6rem",
                    "borderBottom": f"1px solid {COLORS['hairline_strong']}",
                    "marginBottom": "0.6rem",
                    "display": "flex",
                    "justifyContent": "center",
                },
            ),
            # Status tables section (top row)
            html.Div(
                [
                    # Line status table
                    html.Div(
                        [
                            html.Div(
                                "Line Status",
                                style=kicker_style(marginBottom="0.75rem"),
                            ),
                            _create_line_status_table(all_line_ids, line_status),
                        ],
                        style={
                            "flex": "1",
                            "marginRight": "1.25rem",
                        },
                    ),
                    # Station disruptions table
                    html.Div(
                        [
                            html.Div(
                                "Station Status",
                                style=kicker_style(marginBottom="0.75rem"),
                            ),
                            _create_station_status_table(
                                all_stop_ids,
                                stop_disruptions,
                                all_arrivals_data,
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
                    "marginBottom": "2rem",
                },
            ),
            # Arrivals table section (full width below status tables)
            html.Div(
                [
                    _create_arrivals_table(display_arrivals, component_id),
                ],
                style={
                    "width": "100%",
                },
            ),
        ],
        style={
            "color": COLORS["text"],
            # inherit font
        },
    )


def _create_arrivals_table(arrivals: list, component_id: str) -> html.Div:
    """Create the arrivals table for full screen view."""
    if not arrivals:
        return html.Div(
            "No arrivals available",
            style={
                "textAlign": "center",
                "color": COLORS["text_secondary"],
                "fontSize": "1.2rem",
                "padding": "2.5rem",
            },
        )

    # Table header - simplified with fewer columns
    header = html.Div(
        [
            html.Div("Station & Line", style={"flex": "2.5", "fontWeight": "600"}),
            html.Div("Destination", style={"flex": "3", "fontWeight": "600"}),
            html.Div(
                "Transfer Station",
                style={"flex": "1", "fontWeight": "600", "textAlign": "center"},
            ),
            html.Div(
                "Arrival Time",
                style={"flex": "1.5", "fontWeight": "600", "textAlign": "right"},
            ),
        ],
        style={
            **kicker_style(),
            "display": "flex",
            "alignItems": "center",
            "padding": "0.5rem 1.25rem",
            "borderBottom": f"1px solid {COLORS['hairline_strong']}",
            "marginBottom": "0.4rem",
        },
    )

    # Table rows
    rows = []
    for i, arrival in enumerate(arrivals):
        time_color, time_weight = get_time_color_and_weight(arrival["minutes"])

        # Alternate row colors
        bg_color = COLORS["surface"] if i % 2 == 0 else COLORS["surface_raised"]

        # Clean station name - remove "London " prefix
        station_name = arrival["station_name"]
        if station_name.startswith("London "):
            station_name = station_name.replace("London ", "")

        # Use pre-shaped line color and mode icon
        line_color = arrival.get("line_color") or (
            COLORS["urgent"]
            if (arrival.get("mode") or "").lower() == "bus"
            else COLORS["accent"]
        )
        icon_name = arrival.get("icon_name") or (
            "tabler:bus"
            if (arrival.get("mode") or "").lower() == "bus"
            else "material-symbols:train-outline"
        )

        # Format combined time display (actual time and expected)
        actual_time_text = ""
        if arrival.get("arrival_time"):
            dt = arrival["arrival_time"]
            # If naive assume UTC
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=UTC)
            if LONDON_TZ:
                local_time = dt.astimezone(LONDON_TZ)
            else:  # Fallback to system local
                local_time = dt.astimezone()
            actual_time_text = local_time.strftime("%H:%M")

        expected_text = f"{arrival['minutes']}m" if arrival["minutes"] > 0 else "Due"

        # Combine time info: "07:31 (5m)" or just "Due" if due
        if actual_time_text and arrival["minutes"] > 0:
            time_display = f"{actual_time_text} ({expected_text})"
        elif actual_time_text:
            time_display = f"{actual_time_text} (Due)"
        else:
            time_display = expected_text

        row = html.Div(
            [
                # Combined Station & Line column
                html.Div(
                    [
                        html.Div(
                            station_name,
                            style={
                                "color": COLORS["text"],
                                "fontSize": "1rem",
                                "fontWeight": "500",
                                "lineHeight": "1.2",
                            },
                        ),
                        html.Div(
                            [
                                DashIconify(
                                    icon=icon_name,
                                    color=line_color,
                                    style={"width": "1.125rem", "height": "1.125rem"},
                                ),
                                html.Span(
                                    arrival["line_name"],
                                    style={
                                        "color": line_color,
                                        "fontSize": "0.9rem",
                                        "fontWeight": "600",
                                        "lineHeight": "1.2",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "0.375rem",
                                "marginTop": "0.125rem",
                            },
                        ),
                    ],
                    style={"flex": "2.5"},
                ),
                html.Div(
                    arrival["destination"],
                    style={
                        "flex": "3",
                        "alignSelf": "center",
                        "color": COLORS["text"],
                        "fontSize": "1rem",
                    },
                ),
                html.Div(
                    arrival.get("transfer_station_indicator", ""),
                    style={
                        "flex": "1",
                        "color": COLORS["accent"]
                        if arrival.get("transfer_station_indicator")
                        else "transparent",
                        "fontSize": "1.2rem",
                        "alignSelf": "center",
                        "textAlign": "center",
                        "fontWeight": "bold",
                        "title": "Stops at Transfer Station"
                        if arrival.get("transfer_station_indicator")
                        else "",
                    },
                ),
                html.Div(
                    time_display,
                    style={
                        "flex": "1.5",
                        "color": time_color,
                        "fontSize": "1rem",
                        "fontWeight": time_weight,
                        "textAlign": "right",
                        "alignSelf": "center",
                    },
                ),
            ],
            id=f"{component_id}-arrival-row-{i}",
            **{"data-line": (arrival.get("line_name") or "").lower()},
            style=row_style(
                divider=True,
                background=bg_color,
                display="flex",
                alignItems="center",
                padding="0.7rem 1.25rem",
                minHeight="3.75rem",
            ),
        )
        rows.append(row)

    return html.Div([header] + rows, id=f"{component_id}-arrivals-wrapper")


def _create_line_status_table(line_ids: set, line_status: dict) -> html.Div:
    """Create the line status table."""
    if not line_ids or not line_status:
        return html.Div(
            "No line status available",
            style={
                "textAlign": "center",
                "color": COLORS["text_secondary"],
                "fontSize": "1rem",
            },
        )

    rows = []
    for line_id in sorted(line_ids):
        if line_id in line_status:
            status = line_status[line_id]
            status_color = {
                "green": COLORS["accent"],
                "yellow": COLORS["gold"],
                "red": COLORS["urgent"],
            }.get(status["status_color"], COLORS["text_secondary"])

            row = html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                style={
                                    "width": "0.5rem",
                                    "height": "0.5rem",
                                    "borderRadius": "50%",
                                    "background": status_color,
                                    "marginRight": "0.6rem",
                                    "flexShrink": 0,
                                },
                            ),
                            html.Span(
                                status["line_name"],
                                style={
                                    "fontWeight": "500",
                                    "color": COLORS["text"],
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
                style=row_style(
                    divider=True,
                    display="flex",
                    alignItems="center",
                    justifyContent="space-between",
                    borderLeft=f"2px solid {status_color}",
                ),
            )
            rows.append(row)

    return html.Div(rows)


def _create_station_status_table(
    stop_ids: set,
    stop_disruptions: dict,
    all_arrivals_data: dict,
) -> html.Div:
    """Create the station status table."""
    if not stop_ids:
        return html.Div(
            "No stations configured",
            style={
                "textAlign": "center",
                "color": COLORS["text_secondary"],
                "fontSize": "1rem",
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
                                DashIconify(
                                    icon="mdi:alert-circle-outline",
                                    color=COLORS["gold"],
                                    style={
                                        "width": "1.125rem",
                                        "height": "1.125rem",
                                        "marginRight": "0.6rem",
                                        "flexShrink": 0,
                                    },
                                ),
                                html.Span(
                                    station_name,
                                    style={
                                        "fontWeight": "500",
                                        "color": COLORS["text"],
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
                                "color": COLORS["text_secondary"],
                                "fontSize": "0.8rem",
                                "marginTop": "0.3rem",
                            },
                        ),
                    ],
                    style=row_style(
                        divider=True,
                        borderLeft=f"2px solid {COLORS['gold']}",
                    ),
                )
                rows.append(row)

    if not has_disruptions:
        return html.Div(
            [
                html.Div(
                    [
                        DashIconify(
                            icon="mdi:check-circle-outline",
                            color=COLORS["accent"],
                            style={
                                "width": "1.125rem",
                                "height": "1.125rem",
                                "marginRight": "0.6rem",
                                "flexShrink": 0,
                            },
                        ),
                        html.Span(
                            "All stations operating normally",
                            style={
                                "fontWeight": "500",
                                "color": COLORS["accent"],
                                "fontSize": "0.9rem",
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center"},
                ),
            ],
            style=panel_style(
                padding="0.85rem",
                textAlign="center",
                background="rgba(94, 234, 212, 0.06)",
                border=f"1px solid {COLORS['accent']}",
            ),
        )

    return html.Div(rows)
