"""Full-screen agenda for the Google Calendar component."""

import datetime

from dash import html

from utils.dates import local_now
from utils.ui import empty_state, icon

from .data import CalendarEvent
from .summary import event_sort_key, is_birthday

AGENDA_DAYS = 35


def _day_heading(date: datetime.date, today: datetime.date) -> tuple[str, str]:
    delta = (date - today).days
    if delta == 0:
        return "Today", f"{date:%A} {date.day} {date:%B}"
    if delta == 1:
        return "Tomorrow", f"{date:%A} {date.day} {date:%B}"
    if delta < 7:
        return date.strftime("%A"), f"{date.day} {date:%B}"
    return f"{date:%a} {date.day} {date:%b}", f"in {delta} days"


def _range_label(event: CalendarEvent) -> str:
    start, end = event.start_datetime, event.end_datetime
    if event.is_all_day:
        if start.date() == end.date():
            return "All day"
        return f"{start:%a} {start.day} {start:%b} – {end:%a} {end.day} {end:%b}"
    if start.date() == end.date():
        return f"{start:%H:%M} – {end:%H:%M}"
    return f"{start:%a %H:%M} – {end:%a %H:%M}"


def _duration(event: CalendarEvent) -> str:
    if event.is_all_day:
        days = (event.end_datetime.date() - event.start_datetime.date()).days + 1
        return f"{days} days" if days > 1 else ""
    minutes = int((event.end_datetime - event.start_datetime).total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} min"
    hours, rem = divmod(minutes, 60)
    return f"{hours} h {rem} min" if rem else f"{hours} h"


def render_calendar_fullscreen(
    events: list[CalendarEvent],
    colors: dict[str, str],
) -> html.Div:
    """Day-by-day agenda for the coming weeks. A multi-day event is listed
    once, on the first day it's visible (today, if it started earlier),
    with its full date range - rather than repeated on every day it spans.
    """
    now = local_now()
    today = now.date()
    last_day = today + datetime.timedelta(days=AGENDA_DAYS - 1)

    by_day: dict[datetime.date, list[CalendarEvent]] = {}
    for event in events:
        if event.end_datetime.date() < today or event.start_datetime.date() > last_day:
            continue
        if (
            not event.is_all_day
            and event.end_datetime <= now
            and event.start_datetime.date() < today
        ):
            continue
        first_visible = max(event.start_datetime.date(), today)
        by_day.setdefault(first_visible, []).append(event)

    if not by_day:
        return html.Div(
            empty_state("Nothing in the calendar", "mdi:calendar-blank"),
            className="detail",
        )

    days = []
    for date in sorted(by_day):
        heading, sub = _day_heading(date, today)
        rows = [
            _agenda_row(e, colors.get(e.calendar_id, ""), now)
            for e in sorted(by_day[date], key=event_sort_key)
        ]
        days.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(heading, className="agenda-day__title"),
                            html.Span(sub, className="agenda-day__sub"),
                        ],
                        className="agenda-day__head"
                        + (" is-today" if date == today else ""),
                    ),
                    html.Div(rows, className="agenda-day__events"),
                ],
                className="agenda-day card",
            ),
        )
    return html.Div(html.Div(days, className="agenda"), className="detail")


def _agenda_row(event: CalendarEvent, color: str, now: datetime.datetime) -> html.Div:
    past = not event.is_all_day and event.end_datetime <= now
    ongoing = not event.is_all_day and event.start_datetime <= now < event.end_datetime
    time_col = (
        [html.Div("All day", className="agenda-ev__start")]
        if event.is_all_day
        else [
            html.Div(f"{event.start_datetime:%H:%M}", className="agenda-ev__start"),
            html.Div(f"{event.end_datetime:%H:%M}", className="agenda-ev__end"),
        ]
    )
    meta = [
        m
        for m in (_range_label(event) if event.is_multi_day else "", _duration(event))
        if m
    ]
    return html.Div(
        [
            html.Div(time_col, className="agenda-ev__time"),
            html.Span(className="agenda-ev__bar", style={"background": color}),
            html.Div(
                [
                    html.Div(
                        [
                            icon("mdi:cake-variant", "agenda-ev__icon")
                            if is_birthday(event)
                            else None,
                            html.Span(event.title, className="agenda-ev__title"),
                            html.Span("Now", className="ev__now") if ongoing else None,
                        ],
                        className="agenda-ev__title-row",
                    ),
                    html.Div(" · ".join(meta), className="agenda-ev__meta")
                    if meta
                    else None,
                ],
                className="agenda-ev__text",
            ),
        ],
        className="agenda-ev"
        + (" is-past" if past else "")
        + (" is-now" if ongoing else ""),
    )
