from dash import html

from utils.styles import COLORS, FONT_SIZES, WEIGHT

from .constants import MAX_ARRIVAL_WINDOW_MINUTES

# Vertical geometry of the timeline - everything (destination pills, the
# line itself, and both tiers of minute labels) is placed at an absolute
# position *within* this explicitly-sized box, rather than escaping it via
# negative offsets. A box only contributes its own declared height to the
# page's layout - content positioned outside it (e.g. `top: -1.5rem`) is
# invisible to the flexbox sizing that decides how much room this
# component actually gets, so it was liable to get silently clipped by
# the page's `overflow: hidden` safety net whenever the page ran tight on
# space. Reserving real height up front fixes that at the root.
_PILL_TOP = "0"
_LINE_TOP = "1.35rem"
_LABEL_TIER_1_TOP = "1.65rem"
_LABEL_TIER_2_TOP = "2.85rem"
_TIMELINE_HEIGHT = "4rem"


def render_tfl_summary(
    arrivals: list[dict],
    line_status: dict,
    stop_disruptions: dict,
) -> html.Div:
    """Render TFL summary: a legend identifying each line/route by its
    actual brand color, then a single 90-minute timeline marking every
    upcoming arrival across every configured stop - each marker colored
    and lettered by destination so it's identifiable without full text.
    """
    legend = _legend_row(arrivals, line_status, stop_disruptions)

    children: list[html.Div] = []
    if legend is not None:
        children.append(legend)
    children.append(_timeline(arrivals))

    return html.Div(
        children,
        style={
            "color": COLORS["text"],
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.4rem",
        },
    )


def _dot(color: str, size: str = "0.6rem") -> html.Div:
    return html.Div(
        style={
            "width": size,
            "height": size,
            "borderRadius": "50%",
            "background": color,
            "flexShrink": 0,
        },
    )


def _legend_row(
    arrivals: list[dict],
    line_status: dict,
    stop_disruptions: dict,
) -> html.Div | None:
    """One entry per distinct line/route actually showing on the timeline,
    dot colored to match its marker color below.

    A line with real TfL status data (rail/tube lines - bus routes don't
    get one) is always shown prominently with its status word, not just
    when something's wrong: that's specifically the line(s) configured via
    `TFL_LINE_STATUS`, which the user cares about checking at a glance
    every time, not only when it's delayed. Lines without status data
    (bus routes) stay a quiet, compact dot+name - purely a color legend
    for the timeline below.
    """
    seen: dict[str, dict] = {}
    for arrival in arrivals:
        name = arrival.get("line_name") or "?"
        if name not in seen:
            seen[name] = arrival

    entries = []
    for name, arrival in seen.items():
        color = arrival.get("line_color") or COLORS["accent"]
        status = line_status.get(arrival.get("line_id", ""))

        if status:
            status_color = {
                "green": COLORS["accent"],
                "yellow": COLORS["gold"],
                "red": COLORS["urgent"],
            }.get(status["status_color"], COLORS["text_secondary"])
            entries.append(
                html.Div(
                    [
                        _dot(status_color, size="0.7rem"),
                        html.Span(
                            f"{name}: ",
                            style={
                                "fontSize": FONT_SIZES["secondary"],
                                "color": COLORS["text_secondary"],
                            },
                        ),
                        html.Span(
                            status["status_text"],
                            style={
                                "fontSize": FONT_SIZES["secondary"],
                                "fontWeight": WEIGHT["bold"],
                                "color": status_color,
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "0.4rem"},
                ),
            )
        else:
            entries.append(
                html.Div(
                    [
                        _dot(color, size="0.5rem"),
                        html.Span(
                            name,
                            style={
                                "fontSize": FONT_SIZES["small"],
                                "color": COLORS["text_muted"],
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "0.3rem"},
                ),
            )

    if stop_disruptions:
        entries.append(
            html.Div(
                [
                    _dot(COLORS["gold"]),
                    html.Span(
                        "Disruptions",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "fontWeight": WEIGHT["bold"],
                            "color": COLORS["gold"],
                        },
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "gap": "0.3rem"},
            ),
        )

    if not entries:
        return None

    return html.Div(
        entries, style={"display": "flex", "flexWrap": "wrap", "gap": "0.3rem 1.1rem"}
    )


def _contrast_text_color(hex_color: str) -> str:
    """Black or white, whichever reads better on `hex_color`."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    except (ValueError, IndexError):
        return COLORS["text"]
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#0a0a0a" if luminance > 0.6 else "#ffffff"


def _destination_letter(destination: str) -> str:
    destination = (destination or "").strip()
    return destination[0].upper() if destination else "?"


def _timeline(
    arrivals: list[dict], window_minutes: int = MAX_ARRIVAL_WINDOW_MINUTES
) -> html.Div:
    """A single horizontal line spanning "now" to `window_minutes` from now.
    Each upcoming arrival is a small pill on the line: colored by the
    line/route's actual brand color (matching the legend above) and
    lettered with its destination's initial - a compact way to show
    *which service, toward where* without full text - with the minute
    countdown labeled below (imminent arrivals get a red ring instead of
    recoloring the pill, so line identity and urgency are both visible
    at once).
    """
    upcoming = sorted(
        (a for a in arrivals if 0 <= a["minutes"] <= window_minutes),
        key=lambda a: a["minutes"],
    )
    if not upcoming:
        return html.Div(
            "No arrivals in the next 90 minutes",
            style={
                "fontSize": FONT_SIZES["primary"],
                "color": COLORS["text_muted"],
                "padding": "0.4rem 0",
            },
        )

    # Only drop a label to the second tier when it would actually collide
    # with the previous one in the first tier - alternating by position in
    # the list regardless of spacing (the previous approach) made
    # well-separated arrivals on the *same* line jump between tiers for no
    # visible reason, which read as arbitrary/buggy rather than adaptive.
    min_gap_pct = 6.0
    last_tier_1_pct: float | None = None

    markers = []
    for arrival in upcoming:
        pct = (arrival["minutes"] / window_minutes) * 100
        color = arrival.get("line_color") or COLORS["accent"]
        is_urgent = arrival["minutes"] < 2
        label = "Due" if arrival["minutes"] == 0 else f"{arrival['minutes']}m"

        if last_tier_1_pct is None or pct - last_tier_1_pct >= min_gap_pct:
            label_top = _LABEL_TIER_1_TOP
            last_tier_1_pct = pct
        else:
            label_top = _LABEL_TIER_2_TOP

        markers.append(
            html.Div(
                [
                    html.Div(
                        _destination_letter(arrival.get("destination", "")),
                        style={
                            "position": "absolute",
                            "left": f"{pct}%",
                            "top": _PILL_TOP,
                            "width": "1.1rem",
                            "height": "1.1rem",
                            "borderRadius": "50%",
                            "background": color,
                            "color": _contrast_text_color(color),
                            "fontSize": "0.65rem",
                            "fontWeight": WEIGHT["bold"],
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "transform": "translate(-50%, -50%)",
                            "boxShadow": (
                                f"0 0 0 2px {COLORS['urgent']}, 0 0 0 4px {COLORS['bg']}"
                                if is_urgent
                                else f"0 0 0 2px {COLORS['bg']}"
                            ),
                        },
                    ),
                    html.Div(
                        label,
                        style={
                            "position": "absolute",
                            "left": f"{pct}%",
                            "top": label_top,
                            "transform": "translateX(-50%)",
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["urgent"]
                            if is_urgent
                            else COLORS["text_secondary"],
                            "whiteSpace": "nowrap",
                        },
                    ),
                ],
            )
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        "Now",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["text_muted"],
                        },
                    ),
                    html.Span(
                        f"+{window_minutes}m",
                        style={
                            "fontSize": FONT_SIZES["small"],
                            "color": COLORS["text_muted"],
                        },
                    ),
                ],
                style={"display": "flex", "justifyContent": "space-between"},
            ),
            html.Div(
                [
                    html.Div(
                        style={
                            "position": "absolute",
                            "left": "0",
                            "right": "0",
                            "top": _LINE_TOP,
                            "height": "2px",
                            "background": COLORS["hairline_strong"],
                        },
                    ),
                    *markers,
                ],
                style={
                    "position": "relative",
                    "height": _TIMELINE_HEIGHT,
                    "margin": "0.3rem 0.4rem 0 0.4rem",
                },
            ),
        ],
    )
