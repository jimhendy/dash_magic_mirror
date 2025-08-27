"""Utility functions for Google Calendar component.

Contains date parsing, event processing, calendar grid generation,
and other reusable helper functions.
"""

import datetime
from typing import Any

from utils.dates import datetime_from_str


def is_multi_day(start: datetime.datetime, end: datetime.datetime | None) -> bool:
    """Check if event spans multiple days.

    Args:
        start: Event start datetime
        end: Event end datetime (optional)

    Returns:
        True if the event spans multiple days

    """
    if not end:
        return False
    return start.date() != end.date()


def get_corrected_end_date(
    end: datetime.datetime | None,
    *,
    is_all_day: bool,
) -> datetime.datetime | None:
    """Get corrected end date for all-day events.

    Google Calendar all-day events have end dates that are one day too far.

    Args:
        end: Original end datetime
        is_all_day: Whether this is an all-day event

    Returns:
        Corrected end datetime

    """
    if not end:
        return None
    if is_all_day:
        # Subtract 1 day from all-day event end dates
        end -= datetime.timedelta(days=1)
    return end


def get_events_for_date(
    events: list[dict[str, Any]],
    target_date: datetime.date,
) -> list[dict[str, Any]]:
    """Get all events for a specific date.

    Args:
        events: List of event dictionaries
        target_date: Date to filter events for

    Returns:
        List of events that occur on the target date

    """
    events_for_date = []
    for event in events:
        start_dict = event.get("start", {})
        is_all_day = "dateTime" not in start_dict
        start_datetime_str = start_dict.get("dateTime", start_dict.get("date"))
        start_datetime = datetime_from_str(start_datetime_str, is_all_day=is_all_day)

        end_dict = event.get("end", {})
        end_datetime_str = end_dict.get("dateTime", end_dict.get("date"))
        end_datetime = datetime_from_str(end_datetime_str, is_all_day=is_all_day)

        # Correct end date for all-day events
        if is_all_day and end_datetime:
            end_datetime -= datetime.timedelta(days=1)

        # Check if event overlaps with target date
        if (
            start_datetime.date()
            <= target_date
            <= (end_datetime.date() if end_datetime else start_datetime.date())
        ):
            events_for_date.append(event)

    return events_for_date


def generate_calendar_grid(
    year: int,
    month: int,
    events: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Generate calendar grid showing only weeks with events or current week.

    Args:
        year: Target year
        month: Target month
        events: List of event dictionaries

    Returns:
        Calendar grid as list of weeks, each week containing day info dictionaries

    """
    today = datetime.date.today()

    # Get all event dates to determine which weeks we need to show
    event_dates: set[datetime.date] = set()
    for event in events:
        start_date = datetime_from_str(
            event["start"].get("dateTime") or event["start"]["date"],
            is_all_day="date" in event["start"],
        )
        end_date = None
        if event.get("end"):
            end_date = datetime_from_str(
                event["end"].get("dateTime") or event["end"]["date"],
                is_all_day="date" in event["end"],
            )
            end_date = get_corrected_end_date(
                end_date,
                is_all_day="date" in event["start"],
            )

        if not end_date:
            end_date = start_date

        # Add all dates in the event range
        current_date = start_date.date()
        while current_date <= end_date.date():
            event_dates.add(current_date)
            current_date += datetime.timedelta(days=1)

    # Always include current week
    current_week_start = today - datetime.timedelta(days=today.weekday())
    for i in range(7):
        event_dates.add(current_week_start + datetime.timedelta(days=i))

    # Find the range of weeks we need to display
    if not event_dates:
        # If no events, just show current week
        start_date = current_week_start
        weeks_to_show = 1
    else:
        min_date = min(event_dates)
        max_date = max(event_dates)

        # Start from the beginning of the week containing the earliest date
        start_date = min_date - datetime.timedelta(days=min_date.weekday())

        # End at the end of the week containing the latest date
        end_date = max_date + datetime.timedelta(days=(6 - max_date.weekday()))

        # Calculate number of weeks
        weeks_to_show = ((end_date - start_date).days // 7) + 1

        # Limit to reasonable number of weeks (max 8 weeks)
        weeks_to_show = min(weeks_to_show, 8)

    # Create calendar grid
    calendar_grid = []

    for week in range(weeks_to_show):
        week_row = []
        for day in range(7):
            date = start_date + datetime.timedelta(days=week * 7 + day)
            day_events = get_events_for_date(events, date)

            # Check if this date is in the target month (for styling)
            is_current_month = date.month == month

            week_row.append(
                {
                    "date": date,
                    "is_current_month": is_current_month,
                    "is_today": date == today,
                    "is_past": date < today,
                    "events": day_events,
                    "week_index": week,
                    "day_index": day,
                },
            )
        calendar_grid.append(week_row)

    return calendar_grid


def process_multi_day_events(
    calendar_grid: list[list[dict[str, Any]]],
    events: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Process events to create multi-day spans with simple, reliable rendering.

    Args:
        calendar_grid: Calendar grid from generate_calendar_grid
        events: List of event dictionaries

    Returns:
        Dictionary of event spans with rendering information

    """
    event_spans = {}

    # Create a date-to-position mapping for quick lookup
    date_positions = {}
    for week_idx, week in enumerate(calendar_grid):
        for day_idx, day_info in enumerate(week):
            date_positions[day_info["date"]] = (week_idx, day_idx)

    for event in events:
        start_date = datetime_from_str(
            event["start"].get("dateTime") or event["start"]["date"],
            is_all_day="date" in event["start"],
        )
        end_date = None
        if event.get("end"):
            end_date = datetime_from_str(
                event["end"].get("dateTime") or event["end"]["date"],
                is_all_day="date" in event["end"],
            )
            end_date = get_corrected_end_date(
                end_date,
                is_all_day="date" in event["start"],
            )

        if not end_date:
            end_date = start_date

        # Check if this is truly a multi-day event
        start_date_only = start_date.date()
        end_date_only = end_date.date()

        if start_date_only == end_date_only:
            continue  # Skip single-day events

        # Find start and end positions in grid
        start_pos = date_positions.get(start_date_only)
        end_pos = date_positions.get(end_date_only)

        if not start_pos:
            continue  # Event starts outside our grid

        # If event ends outside our grid, find the last day we show
        if not end_pos:
            # Find the last date in our grid
            last_week = calendar_grid[-1]
            last_day = last_week[-1]["date"]
            if end_date_only > last_day:
                end_pos = (len(calendar_grid) - 1, 6)  # Last day of last week
            else:
                continue  # Event ends before our grid starts

        # Create spans for each week this event touches
        start_week, start_day = start_pos
        end_week, end_day = end_pos

        for week_idx in range(start_week, end_week + 1):
            # Determine the start and end days for this week
            if week_idx == start_week:
                week_start_day = start_day
            else:
                week_start_day = 0  # Monday

            if week_idx == end_week:
                week_end_day = end_day
            else:
                week_end_day = 6  # Sunday

            # Create a unique span ID for this week
            span_id = f"event_{hash(event['id']) % 10000}_w{week_idx}"

            event_spans[span_id] = {
                "event": event,
                "week_index": week_idx,
                "start_day": week_start_day,
                "end_day": week_end_day,
                "is_first_week": week_idx == start_week,
                "is_last_week": week_idx == end_week,
                "spans_multiple_weeks": end_week > start_week,
                "event_id": event["id"],
            }

    return event_spans
