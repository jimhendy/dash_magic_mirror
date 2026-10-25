import re

from dash import html

from utils.dates import get_app_timezone
from utils.styles import COLORS, contrast_text
from utils.ui import badge, empty_state, icon

from .constants import MAX_ARRIVAL_WINDOW_MINUTES

TILE_ROWS = 6
PORTRAIT_ROWS = 4  # keep in sync with .board__row:nth-of-type in main.css


def line_badge(arrival: dict, *, compact: bool = False) -> html.Span:
    """A line/route pill in the line's own brand colour."""
    color = arrival.get("line_color") or COLORS["accent"]
    is_bus = (arrival.get("mode") or "").lower() == "bus"
    return html.Span(
        [
            icon("mdi:bus" if is_bus else "mdi:train", "line__icon")
            if not compact
            else None,
            html.Span(arrival.get("line_name") or "?", className="line__name"),
        ],
        className="line",
        style={"background": color, "color": contrast_text(color)},
    )


def format_minutes(minutes: int) -> str:
    return "Due" if minutes <= 0 else f"{minutes} min"


def disrupted_lines(line_status: dict, priority_line_ids: list[str]) -> list[dict]:
    """Statuses of the priority lines (`TFL_LINE_STATUS`) that are not
    running a good service, worst first.
    """
    statuses = [line_status[lid] for lid in priority_line_ids if lid in line_status]
    bad = [s for s in statuses if s["status_color"] != "green"]
    return sorted(bad, key=lambda s: 0 if s["status_color"] == "red" else 1)


def render_tfl_summary(
    arrivals: list[dict],
    *,
    priority_line_ids: list[str] | None = None,
    line_status: dict | None = None,
) -> html.Div:
    """The homepage board: just the lines the household cares about
    (`TFL_LINE_STATUS`; every line if none are set), one row per train,
    with a banner above for any of those lines that is disrupted. Buses
    and everything else are on the detail panel.
    """
    priority = priority_line_ids or []
    alerts = [_status_alert(s) for s in disrupted_lines(line_status or {}, priority)]
    trains = sorted(
        (a for a in arrivals if not priority or a.get("line_id") in priority),
        key=lambda a: a["minutes"],
    )[:TILE_ROWS]
    if not trains:
        return html.Div(
            [
                *alerts,
                empty_state(
                    f"No trains in the next {MAX_ARRIVAL_WINDOW_MINUTES} minutes",
                    "mdi:sleep",
                ),
            ],
            className="board",
        )
    return html.Div([*alerts, *(_row(t) for t in trains)], className="board")


def _status_alert(status: dict) -> html.Div:
    """'<Line>: <status>' with TfL's reason underneath."""
    tone = "bad" if status["status_color"] == "red" else "warn"
    # TfL reasons usually repeat the line and status as a prefix
    # ("WEAVER LINE: Severe delays due to ..."); drop it.
    reason = (status.get("reason") or "").strip()
    if ":" in reason[:40]:
        reason = reason.split(":", 1)[1].strip()
    reason = re.sub(r"(\s*\.)+$", ".", reason)
    # A <section> so `.board__row:nth-of-type` (portrait row cap) skips it.
    return html.Section(
        [
            icon("mdi:alert-circle", "board-alert__icon"),
            html.Div(
                [
                    html.Div(
                        f"{status['line_name']}: {status['status_text']}",
                        className="board-alert__title",
                    ),
                    html.Div(reason, className="board-alert__reason")
                    if reason
                    else None,
                ],
                className="board-alert__text",
            ),
        ],
        className=f"board-alert board-alert--{tone}",
    )


def _row(train: dict) -> html.Div:
    """Clock time | destination, line and stop | countdown."""
    when = train.get("arrival_time")
    clock = (
        when.astimezone(get_app_timezone()).strftime("%H:%M")
        if hasattr(when, "astimezone")
        else ""
    )
    meta = " · ".join(
        part for part in (train.get("line_name"), train.get("station_name")) if part
    )
    minutes = train["minutes"]
    return html.Div(
        [
            html.Div(clock, className="board__clock"),
            html.Div(
                [
                    html.Div(
                        train.get("destination", ""), className="board__dest truncate"
                    ),
                    html.Div(
                        [
                            html.Span(
                                className="board__swatch",
                                style={
                                    "background": train.get("line_color")
                                    or COLORS["accent"]
                                },
                            ),
                            html.Span(meta, className="truncate"),
                        ],
                        className="board__origin",
                    ),
                ],
                className="board__text",
            ),
            html.Div(
                format_minutes(minutes),
                className="board__next" + (" is-urgent" if minutes < 2 else ""),
            ),
        ],
        className="board__row",
    )


def render_tfl_badge(
    line_status: dict,
    stop_disruptions: dict,
    priority_line_ids: list[str],
):
    """Tile header status for the lines the household cares about
    (`TFL_LINE_STATUS`). A disruption is spelled out in a banner on the
    board itself; otherwise the header shows a stop disruption, or just
    a tick for good service.
    """
    if disrupted_lines(line_status, priority_line_ids):
        return None
    if stop_disruptions:
        return badge("Stop disruption", "warn", "mdi:alert-outline")
    if any(lid in line_status for lid in priority_line_ids):
        return html.Span(
            icon("mdi:check-circle", "status-ok__icon"),
            className="status-ok",
            title="Good service",
        )
    return None
