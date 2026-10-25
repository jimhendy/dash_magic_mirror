"""Full-screen month grid for the Google Calendar component."""

import datetime
import math

from dash import html

from utils.dates import local_now
from utils.styles import COLORS, contrast_text
from utils.ui import icon

from .data import CalendarEvent
from .summary import event_sort_key, is_birthday

HORIZON_DAYS = 31
MAX_TIMED_PER_DAY = 4
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def render_calendar_fullscreen(
    events: list[CalendarEvent],
    colors: dict[str, str],
) -> html.Div:
    """A Monday-first calendar grid from the start of this week until the
    next 31 days are covered. All-day and multi-day events are bars that
    run across the days they cover (split at week boundaries); timed
    events are listed in their day's cell.
    """
    now = local_now()
    today = now.date()
    first = today - datetime.timedelta(days=today.weekday())
    weeks = math.ceil((today.weekday() + HORIZON_DAYS) / 7)
    horizon = today + datetime.timedelta(days=HORIZON_DAYS - 1)

    return html.Div(
        [
            html.Div(
                [html.Div(d, className="calm__dow") for d in WEEKDAYS],
                className="calm__head",
            ),
            html.Div(
                [
                    _week(
                        first + datetime.timedelta(weeks=w),
                        events,
                        colors,
                        today,
                        horizon,
                        first_week=w == 0,
                    )
                    for w in range(weeks)
                ],
                className="calm__weeks",
                style={"gridTemplateRows": f"repeat({weeks}, minmax(3.6rem, auto))"},
            ),
        ],
        className="calm",
    )


def _is_bar(event: CalendarEvent) -> bool:
    return event.is_all_day or event.is_multi_day


def _last_day(event: CalendarEvent) -> datetime.date:
    """Inclusive last date (all-day ends are already made inclusive)."""
    end = event.end_datetime
    if not event.is_all_day and end.time() == datetime.time(0, 0):
        end -= datetime.timedelta(minutes=1)
    return max(end.date(), event.start_datetime.date())


def _lanes(segments: list[dict]) -> int:
    """Greedy lane packing so overlapping bars stack instead of colliding.
    Sets `lane` on each segment; returns the number of lanes used.
    """
    ends: list[int] = []
    for seg in sorted(segments, key=lambda s: (s["start"], -(s["end"] - s["start"]))):
        for lane, end in enumerate(ends):
            if end < seg["start"]:
                ends[lane] = seg["end"]
                seg["lane"] = lane
                break
        else:
            seg["lane"] = len(ends)
            ends.append(seg["end"])
    return len(ends)


def _week(
    monday: datetime.date,
    events: list[CalendarEvent],
    colors: dict[str, str],
    today: datetime.date,
    horizon: datetime.date,
    *,
    first_week: bool,
) -> html.Div:
    sunday = monday + datetime.timedelta(days=6)
    segments: list[dict] = []
    timed: dict[int, list[CalendarEvent]] = {}
    for event in sorted(events, key=event_sort_key):
        start, last = event.start_datetime.date(), _last_day(event)
        if last < monday or start > sunday:
            continue
        if _is_bar(event):
            segments.append(
                {
                    "event": event,
                    "start": (max(start, monday) - monday).days,
                    "end": (min(last, sunday) - monday).days,
                    "cont_left": start < monday,
                    "cont_right": last > sunday,
                },
            )
        else:
            timed.setdefault((start - monday).days, []).append(event)

    lanes = _lanes(segments)
    children: list = []
    for col in range(7):
        date = monday + datetime.timedelta(days=col)
        classes = ["calm__day"]
        if date < today:
            classes.append("is-past")
        if date == today:
            classes.append("is-today")
        if date > horizon:
            classes.append("is-beyond")
        if col >= 5:
            classes.append("is-weekend")
        # Month name on the 1st, and on the first cell so the grid opens
        # with one.
        month = f"{date:%b}" if date.day == 1 or (first_week and col == 0) else ""
        children.append(
            html.Div(
                [
                    html.Span(str(date.day), className="calm__num"),
                    html.Span(month, className="calm__mon") if month else None,
                ],
                className=" ".join(classes),
                style={"gridColumn": col + 1, "gridRow": "1 / -1"},
            ),
        )
    for seg in segments:
        children.append(_bar(seg, colors))
    for col, day_events in timed.items():
        shown = day_events[:MAX_TIMED_PER_DAY]
        extra = len(day_events) - len(shown)
        children.append(
            html.Div(
                [
                    *(_timed(e, colors) for e in shown),
                    html.Div(f"+{extra} more", className="calm__more")
                    if extra
                    else None,
                ],
                className="calm__timed",
                style={"gridColumn": col + 1, "gridRow": lanes + 2},
            ),
        )
    return html.Div(
        children,
        className="calm__week",
        # Row 1 is a fixed band for the date numbers: the day cells span
        # every row, so nothing else would give it a height.
        style={
            "gridTemplateRows": f"2.4rem repeat({lanes}, auto) 1fr",
        },
    )


def _bar(seg: dict, colors: dict[str, str]) -> html.Div:
    event = seg["event"]
    color = colors.get(event.calendar_id) or COLORS["accent"]
    classes = ["calm__bar"]
    if seg["cont_left"]:
        classes.append("is-cont-left")
    if seg["cont_right"]:
        classes.append("is-cont-right")
    when = (
        "" if event.is_all_day or seg["cont_left"] else f"{event.start_datetime:%H:%M} "
    )
    return html.Div(
        [
            icon("mdi:cake-variant", "calm__bar-icon") if is_birthday(event) else None,
            html.Span(when + event.title, className="truncate"),
        ],
        className=" ".join(classes),
        style={
            "gridColumn": f"{seg['start'] + 1} / {seg['end'] + 2}",
            "gridRow": seg["lane"] + 2,
            "background": color,
            "color": contrast_text(color),
        },
    )


def _timed(event: CalendarEvent, colors: dict[str, str]) -> html.Div:
    color = colors.get(event.calendar_id) or COLORS["accent"]
    return html.Div(
        [
            html.Span(className="calm__dot", style={"background": color}),
            html.Span(f"{event.start_datetime:%H:%M}", className="calm__time"),
            html.Span(event.title, className="calm__title"),
        ],
        className="calm__ev",
    )
