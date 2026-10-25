from dash import html

from utils.dates import get_app_timezone
from utils.styles import COLORS, contrast_text
from utils.ui import badge, empty_state, icon

from .constants import MAX_ARRIVAL_WINDOW_MINUTES

TILE_ROWS = 7
PRIMARY_ROWS = 5  # keep in sync with .board__row:nth-child in main.css
TIMES_PER_ROW = 5


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


def group_departures(arrivals: list[dict]) -> list[dict]:
    """Collapse individual arrivals into one row per (line, destination),
    each with its upcoming minute countdowns, soonest row first.
    """
    groups: dict[tuple[str, str], dict] = {}
    for arrival in sorted(arrivals, key=lambda a: a["minutes"]):
        key = (arrival.get("line_id", ""), arrival.get("destination", ""))
        group = groups.setdefault(key, {"first": arrival, "minutes": [], "via": False})
        group["minutes"].append(arrival["minutes"])
        group["via"] = group["via"] or bool(arrival.get("via_transfer"))
    return sorted(groups.values(), key=lambda g: g["minutes"][0])


def render_tfl_summary(
    arrivals: list[dict],
    *,
    priority_line_ids: list[str] | None = None,
) -> html.Div:
    """A compact departure board: one row per line + destination with the
    next few countdowns. Rows for the configured priority lines
    (`TFL_LINE_STATUS`) are always kept even when buses are sooner.
    """
    groups = group_departures(arrivals)
    if not groups:
        return empty_state(
            f"No departures in the next {MAX_ARRIVAL_WINDOW_MINUTES} minutes",
            "mdi:sleep",
        )

    # The first PRIMARY_ROWS are what portrait shows (CSS hides the rest);
    # priority-line rows are guaranteed a place among them.
    priority = set(priority_line_ids or [])
    primary = [g for g in groups if g["first"].get("line_id") in priority][:2]
    primary += [g for g in groups if g not in primary][: PRIMARY_ROWS - len(primary)]
    primary.sort(key=lambda g: g["minutes"][0])
    extra = [g for g in groups if g not in primary][: TILE_ROWS - len(primary)]
    chosen = primary + extra

    return html.Div([_row(g) for g in chosen], className="board")


def _origin(first: dict) -> str:
    """'from <stop> · <clock time>' for a row's soonest departure."""
    parts = []
    if first.get("station_name"):
        parts.append(f"from {first['station_name']}")
    when = first.get("arrival_time")
    if when is not None and hasattr(when, "astimezone"):
        parts.append(when.astimezone(get_app_timezone()).strftime("%H:%M"))
    return " · ".join(parts)


def _row(group: dict) -> html.Div:
    first = group["first"]
    minutes = group["minutes"][:TIMES_PER_ROW]
    soonest = minutes[0]
    return html.Div(
        [
            line_badge(first),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                first.get("destination", ""), className="truncate"
                            ),
                            icon("mdi:swap-horizontal-circle", "board__via")
                            if group["via"]
                            else None,
                        ],
                        className="board__dest",
                    ),
                    html.Div(_origin(first), className="board__origin truncate"),
                ],
                className="board__text",
            ),
            html.Div(
                [
                    html.Span(
                        format_minutes(soonest),
                        className="board__next" + (" is-urgent" if soonest < 2 else ""),
                    ),
                    html.Span(
                        ", ".join(str(m) for m in minutes[1:]) + " min",
                        className="board__later",
                    )
                    if len(minutes) > 1
                    else None,
                ],
                className="board__times",
            ),
        ],
        className="board__row",
    )


def render_tfl_badge(
    line_status: dict,
    stop_disruptions: dict,
    priority_line_ids: list[str],
):
    """Service status for the lines the household actually cares about
    (`TFL_LINE_STATUS`): worst status first, then stop disruptions, else
    a reassuring "Good service".
    """
    statuses = [
        line_status[lid] for lid in priority_line_ids if lid in line_status
    ] or list(
        line_status.values(),
    )
    bad = [s for s in statuses if s["status_color"] != "green"]
    if bad:
        worst = min(bad, key=lambda s: 0 if s["status_color"] == "red" else 1)
        tone = "bad" if worst["status_color"] == "red" else "warn"
        return badge(
            f"{worst['line_name']}: {worst['status_text']}",
            tone,
            "mdi:alert-circle-outline",
        )
    if stop_disruptions:
        return badge("Stop disruption", "warn", "mdi:alert-outline")
    if statuses:
        name = statuses[0]["line_name"] if len(statuses) == 1 else "Lines"
        return badge(f"{name}: Good service", "good", "mdi:check-circle-outline")
    return None
