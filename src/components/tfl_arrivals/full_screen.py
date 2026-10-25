from dash import html

from utils.ui import empty_state, filter_chips, icon, section

from .summary import format_minutes, line_badge

_STATUS_TONE = {"green": "good", "yellow": "warn", "red": "bad"}


def render_tfl_fullscreen(
    arrivals_by_stop: dict[str, dict],
    line_status: dict,
    stop_disruptions: dict,
) -> html.Div:
    """Every configured stop's live departures (all directions), line status
    and stop disruptions, with a line filter.
    """
    lines: dict[str, str] = {}
    for stop in arrivals_by_stop.values():
        for arrival in stop.get("arrivals", []):
            name = arrival.get("line_name") or ""
            if name:
                lines[name.lower()] = name

    children = []
    if len(lines) > 1:
        children.append(
            filter_chips(
                "tfl-line",
                sorted(lines.items(), key=lambda kv: kv[1].casefold()),
            ),
        )

    children.append(
        html.Div(
            [_stop_card(stop_id, stop) for stop_id, stop in arrivals_by_stop.items()],
            className="stop-grid",
        ),
    )

    if line_status:
        children.append(
            section("Line status", _status_list(line_status), class_name="card")
        )

    if stop_disruptions:
        names = {
            sid: s.get("station_name") or sid for sid, s in arrivals_by_stop.items()
        }
        children.append(
            section(
                "Disruptions",
                html.Div(
                    [
                        html.Div(
                            [
                                icon("mdi:alert-outline", "disruption__icon"),
                                html.Div(
                                    [
                                        html.Div(
                                            names.get(stop_id, stop_id),
                                            className="disruption__stop",
                                        ),
                                        html.Div(
                                            d.get("description", ""),
                                            className="disruption__text",
                                        ),
                                    ],
                                ),
                            ],
                            className="disruption",
                        )
                        for stop_id, items in stop_disruptions.items()
                        for d in items
                    ],
                    className="disruptions",
                ),
                class_name="card",
            ),
        )

    return html.Div(children, className="detail tfl-detail")


def _stop_card(stop_id: str, stop: dict) -> html.Div:
    arrivals = sorted(stop.get("arrivals", []), key=lambda a: a["minutes"])
    is_bus = any((a.get("mode") or "").lower() == "bus" for a in arrivals)
    rows = [
        html.Div(
            [
                line_badge(a, compact=True),
                html.Div(
                    [
                        html.Div(
                            a.get("destination", ""), className="dep__dest truncate"
                        ),
                        html.Div(
                            [
                                _platform_label(a),
                                html.Span(
                                    [
                                        icon("mdi:swap-horizontal-circle", "ic"),
                                        "Stops at interchange",
                                    ],
                                    className="dep__via",
                                )
                                if a.get("via_transfer")
                                else None,
                            ],
                            className="dep__meta",
                        ),
                    ],
                    className="dep__text",
                ),
                html.Div(
                    format_minutes(a["minutes"]),
                    className="dep__mins" + (" is-urgent" if a["minutes"] < 2 else ""),
                ),
            ],
            className="dep",
            **{"data-filter-key": (a.get("line_name") or "").lower()},
        )
        for a in arrivals
    ]
    return html.Div(
        [
            html.Div(
                [
                    icon(
                        "mdi:bus-stop" if is_bus else "mdi:train-variant", "stop__icon"
                    ),
                    html.Div(
                        stop.get("station_name") or stop_id,
                        className="stop__name truncate",
                    ),
                    html.Span(f"{len(arrivals)}", className="stop__count"),
                ],
                className="stop__head",
            ),
            html.Div(rows, className="deps")
            if rows
            else empty_state("No departures soon", "mdi:sleep"),
        ],
        className="card stop",
    )


def _platform_label(arrival: dict) -> str:
    platform = (arrival.get("platform") or "").strip()
    if not platform or platform in {"Unknown", "null"}:
        return (arrival.get("direction") or "").title()
    if (arrival.get("mode") or "").lower() == "bus":
        return f"Stop {platform}"
    # TfL rail usually sends "Platform 2" already; tube sends "Eastbound - Platform 1".
    return platform if "platform" in platform.lower() else f"Platform {platform}"


def _status_list(line_status: dict) -> html.Div:
    rows = []
    for status in sorted(line_status.values(), key=lambda s: s["line_name"].casefold()):
        tone = _STATUS_TONE.get(status["status_color"], "neutral")
        rows.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(status["line_name"], className="status__line"),
                            html.Span(
                                status["status_text"], className=f"badge badge--{tone}"
                            ),
                        ],
                        className="status__head",
                    ),
                    html.Div(status["reason"], className="status__reason")
                    if status.get("reason")
                    else None,
                ],
                className="status",
            ),
        )
    return html.Div(rows, className="statuses")
