"""Dashboard tile for the Google Calendar component: today, tomorrow and
the rest of the week."""

import datetime

from dash import html

from utils.dates import local_now
from utils.styles import with_alpha
from utils.ui import badge, icon

from .data import CalendarEvent, get_events_for_date

MAX_TIMED_PER_DAY = 6


def is_birthday(event: CalendarEvent) -> bool:
    return "birthday" in event.title.lower()


def event_sort_key(event: CalendarEvent):
    return (not event.is_all_day, event.start_datetime, event.title.casefold())


def all_day_pill(
    event: CalendarEvent, color: str, label: str | None = None
) -> html.Div:
    return html.Div(
        [
            icon("mdi:cake-variant", "pill__icon")
            if is_birthday(event)
            else html.Span(className="pill__dot"),
            html.Span(event.title, className="truncate"),
            html.Span(label, className="pill__label") if label else None,
        ],
        className="pill",
        style={"--ev": color, "background": with_alpha(color, 0.16)},
    )


def render_calendar_summary(
    events: list[CalendarEvent],
    colors: dict[str, str],
) -> html.Div:
    today = local_now().date()
    tomorrow = today + datetime.timedelta(days=1)
    return html.Div(
        [
            _day_column("Today", today, events, colors),
            _day_column("Tomorrow", tomorrow, events, colors),
        ],
        className="cal-tile",
    )


def _day_column(
    label: str,
    date: datetime.date,
    events: list[CalendarEvent],
    colors: dict[str, str],
) -> html.Div:
    day_events = sorted(get_events_for_date(events, date), key=event_sort_key)
    all_day = [e for e in day_events if e.is_all_day]
    timed = [e for e in day_events if not e.is_all_day]
    visible = timed[:MAX_TIMED_PER_DAY]
    hidden = len(timed) - len(visible)

    body: list = [all_day_pill(e, colors.get(e.calendar_id, "")) for e in all_day]
    body.extend(_timed_row(e, date, colors.get(e.calendar_id, "")) for e in visible)
    if hidden > 0:
        body.append(html.Div(f"+{hidden} more", className="more"))
    if not body:
        body.append(html.Div("Nothing planned", className="cal-empty"))

    return html.Div(
        [
            html.Div(
                [
                    html.Span(label, className="cal-col__label"),
                    html.Span(f"{date:%a} {date.day}", className="cal-col__date"),
                ],
                className="cal-col__head",
            ),
            html.Div(body, className="cal-col__body"),
        ],
        className="cal-col",
    )


def _timed_row(event: CalendarEvent, date: datetime.date, color: str) -> html.Div:
    now = local_now()
    starts_today = event.start_datetime.date() == date
    if starts_today:
        time_label = event.start_datetime.strftime("%H:%M")
    elif event.end_datetime.date() == date:
        time_label = f"–{event.end_datetime:%H:%M}"
    else:
        time_label = "All day"

    state = ""
    if event.end_datetime <= now:
        state = " is-past"
    elif event.start_datetime <= now < event.end_datetime:
        state = " is-now"

    return html.Div(
        [
            html.Span(className="ev__bar", style={"background": color}),
            html.Span(time_label, className="ev__time"),
            html.Span(event.title, className="ev__title truncate"),
            html.Span("Now", className="ev__now") if state == " is-now" else None,
        ],
        className="ev" + state,
    )


def render_calendar_badge(events: list[CalendarEvent]):
    """The next thing coming up today, if anything."""
    now = local_now()
    upcoming = sorted(
        (
            e
            for e in events
            if not e.is_all_day
            and e.start_datetime > now
            and e.start_datetime.date() == now.date()
        ),
        key=lambda e: e.start_datetime,
    )
    if upcoming:
        nxt = upcoming[0]
        return badge(f"Next {nxt.start_datetime:%H:%M}", "info", "mdi:clock-outline")
    return None
