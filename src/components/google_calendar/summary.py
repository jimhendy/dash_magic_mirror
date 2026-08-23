"""Summary view rendering for Google Calendar component."""

import datetime

from dash import html

from utils.calendar import (
    get_contrasting_text_color,
    get_event_color_by_event,
    truncate_event_title,
)
from utils.dates import local_today
from utils.styles import COLORS, FONT_SIZES, WEIGHT, kicker_style

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

    multi_day_events = []
    single_today_events = []
    single_tomorrow_events = []

    for event in all_events:
        start_date = event.start_datetime.date()
        end_date = event.end_datetime.date()
        if start_date <= today and end_date >= tomorrow:
            multi_day_events.append(event)
        else:
            if start_date == today or (start_date < today and end_date == today):
                single_today_events.append(event)
            if start_date == tomorrow or (
                start_date < tomorrow and end_date == tomorrow
            ):
                single_tomorrow_events.append(event)

    return html.Div(
        [
            html.Span("Calendar", style=kicker_style()),
            html.Div(
                style={"display": "flex", "flexDirection": "column", "gap": "0.4rem"},
                children=[
                    _render_multi_day_event(event, today, tomorrow)
                    for event in multi_day_events
                ],
            )
            if multi_day_events
            else None,
            html.Div(
                style={"display": "flex", "gap": "1.5rem"},
                children=[
                    _render_day_column(
                        today,
                        single_today_events,
                        covered_by_multi_day=bool(multi_day_events),
                    ),
                    _render_day_column(
                        tomorrow,
                        single_tomorrow_events,
                        covered_by_multi_day=bool(multi_day_events),
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


def _render_multi_day_event(
    event: CalendarEvent,
    today: datetime.date,
    tomorrow: datetime.date,
) -> html.Div:
    """A continuous colored bar for an event spanning today and tomorrow -
    the one place a filled block is the *right* call (it reads as a single
    connected span, the way Google/Outlook calendars render multi-day
    events), not a decorative box around static text.
    """
    background = get_event_color_by_event(event.id)
    text_color = get_contrasting_text_color(background)
    return html.Div(
        truncate_event_title(event.title, 60),
        style={
            "background": background,
            "color": text_color,
            "borderRadius": "0.4rem",
            "padding": "0.35rem 0.7rem",
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
    events: list[CalendarEvent],
    *,
    covered_by_multi_day: bool = False,
) -> html.Div:
    """Render a single day column: plain event rows, colored only by a thin
    left accent bar per event. Which column is "today" vs "tomorrow" is
    obvious from position alone, so no label is rendered.

    `covered_by_multi_day` means a multi-day event bar (rendered above both
    columns) already spans this day - so an empty `events` list here isn't
    actually an empty day, and "Nothing scheduled" would be wrong.
    """
    visible = events[:_MAX_EVENTS_PER_DAY]
    overflow_count = len(events) - len(visible)

    if visible:
        rows = [_render_event(event, date) for event in visible]
    elif covered_by_multi_day:
        rows = []
    else:
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
