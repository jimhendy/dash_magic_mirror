"""Summary view rendering for Google Calendar component."""

import datetime

from dash import html

from utils.calendar import (
    get_contrasting_text_color,
    get_event_color_by_event,
    truncate_event_title,
)
from utils.dates import local_today
from utils.styles import COLORS, FONT_SIZES, RADIUS, WEIGHT

from .data import CalendarEvent, get_events_for_date
from .utils import generate_event_time_display, prepare_events_for_rendering


def render_calendar_summary(events: list[CalendarEvent]) -> html.Div:
    """Render the calendar summary view showing today and tomorrow.

    Args:
        events: List of processed calendar events

    Returns:
        html.Div containing the calendar summary layout

    """
    sorted_events = prepare_events_for_rendering(events)

    today = local_today()
    tomorrow = today + datetime.timedelta(days=1)

    today_events = get_events_for_date(sorted_events, today)
    tomorrow_events = get_events_for_date(sorted_events, tomorrow)

    all_events = []
    seen_ids = set()
    for event in today_events + tomorrow_events:
        if event.id not in seen_ids:
            seen_ids.add(event.id)
            all_events.append(event)

    # All-day events (single-day or multi-day - a birthday, a holiday, a
    # multi-day trip) always render as a solid colored bar, never in the
    # plain accent-line list below: that's what actually distinguishes "no
    # specific time, applies to the whole day" from a scheduled meeting.
    # One spanning both today and tomorrow (a contiguous date range, so it
    # touches both days iff its start is <= today and its end is >=
    # tomorrow) gets a single bar above both columns; the rest are scoped
    # to just the one day column they belong to.
    spanning_all_day_events = []
    today_all_day_events = []
    tomorrow_all_day_events = []
    today_timed_events = []
    tomorrow_timed_events = []

    for event in all_events:
        start_date = event.start_datetime.date()
        end_date = event.end_datetime.date()
        touches_today = start_date <= today <= end_date
        touches_tomorrow = start_date <= tomorrow <= end_date

        if event.is_all_day:
            if touches_today and touches_tomorrow:
                spanning_all_day_events.append(event)
            else:
                if touches_today:
                    today_all_day_events.append(event)
                if touches_tomorrow:
                    tomorrow_all_day_events.append(event)
        else:
            if touches_today:
                today_timed_events.append(event)
            if touches_tomorrow:
                tomorrow_timed_events.append(event)

    covered_by_spanning = bool(spanning_all_day_events)

    return html.Div(
        [
            html.Div(
                style={"display": "flex", "flexDirection": "column", "gap": "0.4rem"},
                children=[
                    _render_all_day_bar(event, today, tomorrow)
                    for event in spanning_all_day_events
                ],
            )
            if spanning_all_day_events
            else None,
            html.Div(
                style={"display": "flex", "gap": "1.5rem"},
                children=[
                    _render_day_column(
                        today,
                        all_day_events=today_all_day_events,
                        timed_events=today_timed_events,
                        covered_by_spanning=covered_by_spanning,
                    ),
                    _render_day_column(
                        tomorrow,
                        all_day_events=tomorrow_all_day_events,
                        timed_events=tomorrow_timed_events,
                        covered_by_spanning=covered_by_spanning,
                    ),
                ],
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.6rem",
            "width": "100%",
        },
    )


def _render_all_day_bar(
    event: CalendarEvent,
    window_start: datetime.date,
    window_end: datetime.date,
) -> html.Div:
    """A continuous colored bar for an all-day event, scoped to the given
    `window_start`/`window_end` (either a single day, or today+tomorrow for
    one spanning both) - the one place a filled block is the *right* call
    (it reads as a single connected span, the way Google/Outlook calendars
    render all-day events), not a decorative box around static text.

    The bar's corners read as a real timeline segment rather than a plain
    rounded rectangle: an edge that's the event's actual start/end gets a
    full pill-rounded cap, while an edge that's merely where the visible
    window cuts off an event continuing before or after it stays square -
    the same "cut off vs. terminates here" convention Google/Outlook
    calendars use for multi-day bars.
    """
    background = get_event_color_by_event(event.id)
    text_color = get_contrasting_text_color(background)
    starts_here = event.start_datetime.date() == window_start
    ends_here = event.end_datetime.date() == window_end
    left_radius = RADIUS["pill"] if starts_here else "0"
    right_radius = RADIUS["pill"] if ends_here else "0"
    return html.Div(
        truncate_event_title(event.title, 60),
        style={
            "background": background,
            "color": text_color,
            "borderRadius": f"{left_radius} {right_radius} {right_radius} {left_radius}",
            "padding": "0.35rem 0.9rem",
            "fontSize": "1.32rem",  # meta (1.1rem) + 20%, calendar events read too small
            "fontWeight": WEIGHT["semibold"],
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "whiteSpace": "nowrap",
        },
    )


_MAX_EVENTS_PER_DAY = 4


def _render_day_column(
    date: datetime.date,
    *,
    all_day_events: list[CalendarEvent],
    timed_events: list[CalendarEvent],
    covered_by_spanning: bool = False,
) -> html.Div:
    """Render a single day column: any all-day events as solid bars first,
    then plain timed-event rows colored only by a thin left accent bar.
    Which column is "today" vs "tomorrow" is obvious from position alone,
    so no label is rendered.

    `covered_by_spanning` means an all-day bar spanning both columns
    (rendered above both) already covers this day - so no all-day and no
    timed events here isn't actually an empty day, and "Nothing scheduled"
    would be wrong.
    """
    visible = timed_events[:_MAX_EVENTS_PER_DAY]
    overflow_count = len(timed_events) - len(visible)

    rows: list[html.Div] = [
        _render_all_day_bar(event, date, date) for event in all_day_events
    ]
    rows.extend(_render_event(event, date) for event in visible)

    if not rows and not covered_by_spanning:
        rows = [
            html.Div(
                "Nothing scheduled",
                style={"fontSize": FONT_SIZES["meta"], "color": COLORS["text_muted"]},
            ),
        ]
    if overflow_count > 0:
        rows.append(
            html.Div(
                f"+{overflow_count} more",
                style={"fontSize": FONT_SIZES["small"], "color": COLORS["text_muted"]},
            ),
        )

    return html.Div(
        style={
            "flex": "1",
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.3rem",
            "minWidth": "0",
            "overflow": "hidden",
        },
        children=rows,
    )


def _render_event(event: CalendarEvent, display_date: datetime.date) -> html.Div:
    """A single event: a thin left accent bar for color-coding, plain text
    otherwise - no background box, no full border.
    """
    event_starts_here = event.start_datetime.date() == display_date
    event_ends_here = event.end_datetime.date() == display_date
    accent_color = get_event_color_by_event(event.id)
    time_display = generate_event_time_display(
        event,
        event_starts_here,
        event_ends_here,
    )

    return html.Div(
        [
            html.Div(
                truncate_event_title(event.title, 40),
                style={
                    "fontSize": "1.32rem",  # meta (1.1rem) + 20%, calendar events read too small
                    "fontWeight": WEIGHT["regular"],
                    "color": COLORS["text"],
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                },
            ),
            html.Div(
                time_display,
                style={
                    "fontSize": "1.14rem",  # small (0.95rem) + 20%
                    "color": COLORS["text_muted"],
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                },
            )
            if time_display
            else None,
        ],
        style={
            "borderLeft": f"3px solid {accent_color}",
            "padding": "0.4rem 0 0.4rem 0.6rem",
        },
    )
