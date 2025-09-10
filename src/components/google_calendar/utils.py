"""Calendar-specific utility functions for Google Calendar component."""

import datetime
from typing import Any

from utils.calendar import assign_event_colors_consistently

from .data import CalendarEvent


def prepare_events_for_rendering(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """Prepare events for rendering with consistent color assignment and sorting.

    Args:
        events: List of raw calendar events

    Returns:
        Sorted events with colors assigned consistently

    """
    # Assign colors consistently based on today's events having priority
    assign_event_colors_consistently(events, datetime.date.today())

    # Sort events by start date, then by title for consistent color assignment
    # Handle timezone-aware/naive datetime comparison by using date() for sorting
    try:
        sorted_events = sorted(events, key=lambda e: (e.start_datetime.date(), e.title))
    except (TypeError, AttributeError):
        # Fallback: if there are issues with datetime comparison, sort by title only
        sorted_events = sorted(events, key=lambda e: e.title)

    return sorted_events


def get_common_event_styles() -> dict[str, Any]:
    """Get common styling properties for calendar events.

    Returns:
        Dictionary of common CSS properties

    """
    return {
        "padding": "6px 8px",
        "fontSize": "12px",
        "lineHeight": "1.2",
        "fontWeight": "600",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "whiteSpace": "nowrap",
        "borderRadius": "4px",
        "boxShadow": "0 1px 3px rgba(0, 0, 0, 0.3)",
    }


def calculate_event_border_radius(
    event_starts_here: bool,
    event_ends_here: bool,
    radius: str = "8px",
) -> str:
    """Calculate border radius for an event based on where it starts/ends.

    Args:
        event_starts_here: Whether the event starts on this display unit
        event_ends_here: Whether the event ends on this display unit
        radius: Base radius to use

    Returns:
        CSS border-radius string

    """
    left_radius = radius if event_starts_here else "0px"
    right_radius = radius if event_ends_here else "0px"
    return f"{left_radius} {right_radius} {right_radius} {left_radius}"


def calculate_event_margins(
    event_starts_here: bool,
    event_ends_here: bool,
    edge_margin: str = "4px",
    continuation_margin: str = "-8px",
) -> tuple[str, str]:
    """Calculate margins for an event based on where it starts/ends.

    Args:
        event_starts_here: Whether the event starts on this display unit
        event_ends_here: Whether the event ends on this display unit
        edge_margin: Margin to use when event starts/ends here
        continuation_margin: Margin to use when event continues from elsewhere

    Returns:
        Tuple of (left_margin, right_margin)

    """
    margin_left = edge_margin if event_starts_here else continuation_margin
    margin_right = edge_margin if event_ends_here else continuation_margin
    return margin_left, margin_right


def generate_event_time_display(
    event: CalendarEvent,
    event_starts_here: bool,
    event_ends_here: bool,
) -> str:
    """Generate time display string for an event based on its timing.

    Args:
        event: Calendar event
        event_starts_here: Whether the event starts on this display unit
        event_ends_here: Whether the event ends on this display unit

    Returns:
        Formatted time display string

    """
    if event.is_all_day:
        return ""

    if event_starts_here and event_ends_here:
        # Same day event
        return f"{event.start_datetime.strftime('%H:%M')} - {event.end_datetime.strftime('%H:%M')}"
    if event_starts_here:
        # Starts here, continues
        return f"From {event.start_datetime.strftime('%H:%M')}"
    if event_ends_here:
        # Ends here
        return f"Until {event.end_datetime.strftime('%H:%M')}"
    # Continues all day
    return "All day"


def generate_calendar_grid_weeks(
    start_date: datetime.date,
    num_weeks: int,
    events: list[CalendarEvent],
) -> list[list[dict[str, Any]]]:
    """Generate a calendar grid for a specified number of weeks.

    Args:
        start_date: Starting date (should be a Monday)
        num_weeks: Number of weeks to generate
        events: List of CalendarEvent objects

    Returns:
        Calendar grid as list of weeks, each week containing day info dictionaries

    """
    today = datetime.date.today()
    calendar_grid = []

    # Ensure start_date is a Monday
    days_since_monday = start_date.weekday()
    actual_start = start_date - datetime.timedelta(days=days_since_monday)

    for week_idx in range(num_weeks):
        week_row = []
        for day_idx in range(7):  # Monday to Sunday
            current_date = actual_start + datetime.timedelta(
                days=week_idx * 7 + day_idx,
            )

            # Get events for this date
            day_events = [
                event
                for event in events
                if event.start_datetime.date()
                <= current_date
                <= event.end_datetime.date()
            ]

            week_row.append(
                {
                    "date": current_date,
                    "is_today": current_date == today,
                    "is_past": current_date < today,
                    "events": day_events,
                    "week_index": week_idx,
                    "day_index": day_idx,
                },
            )
        calendar_grid.append(week_row)

    return calendar_grid


def create_event_spans(
    calendar_grid: list[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Create event spans that connect multi-day events across the calendar grid.

    Args:
        calendar_grid: Calendar grid from generate_calendar_grid_weeks

    Returns:
        List of event span dictionaries with positioning information

    """
    event_spans = []
    processed_events = set()

    # Flatten the grid to get all dates and their positions
    date_positions = {}
    for week_idx, week in enumerate(calendar_grid):
        for day_idx, day_info in enumerate(week):
            date_positions[day_info["date"]] = (week_idx, day_idx)

    # Track events by week for vertical stacking
    week_event_tracks = {}

    # Process each day to find event spans
    for week_idx, week in enumerate(calendar_grid):
        for day_idx, day_info in enumerate(week):
            for event in day_info["events"]:
                event_key = (event.id, event.start_datetime.date())

                # Skip if we've already processed this event
                if event_key in processed_events:
                    continue

                processed_events.add(event_key)

                # Calculate event span
                start_date = max(
                    event.start_datetime.date(),
                    min(date_positions.keys()),
                )
                end_date = min(event.end_datetime.date(), max(date_positions.keys()))

                # Find start and end positions in grid
                start_week, start_day = date_positions.get(
                    start_date,
                    (week_idx, day_idx),
                )
                end_week, end_day = date_positions.get(end_date, (week_idx, day_idx))

                # Assign vertical track for each week this event spans
                event_track = 0
                for week in range(start_week, end_week + 1):
                    if week not in week_event_tracks:
                        week_event_tracks[week] = []

                    # Find available track (to avoid overlaps)
                    used_tracks = set()
                    for existing_event in week_event_tracks[week]:
                        # Check if events overlap in this week
                        existing_start = existing_event["start_week"]
                        existing_end = existing_event["end_week"]
                        existing_start_day = (
                            existing_event["start_day"] if existing_start == week else 0
                        )
                        existing_end_day = (
                            existing_event["end_day"] if existing_end == week else 6
                        )

                        current_start_day = start_day if start_week == week else 0
                        current_end_day = end_day if end_week == week else 6

                        # Check for day overlap
                        if not (
                            current_end_day < existing_start_day
                            or current_start_day > existing_end_day
                        ):
                            used_tracks.add(existing_event["track"])

                    # Find first available track
                    event_track = 0
                    while event_track in used_tracks:
                        event_track += 1

                # Create event span
                event_span = {
                    "event": event,
                    "start_week": start_week,
                    "start_day": start_day,
                    "end_week": end_week,
                    "end_day": end_day,
                    "start_date": start_date,
                    "end_date": end_date,
                    "track": event_track,
                }

                event_spans.append(event_span)

                # Add to week tracking
                for week in range(start_week, end_week + 1):
                    week_event_tracks[week].append(event_span)

    return event_spans


def get_calendar_title_for_weeks(calendar_grid: list[list[dict[str, Any]]]) -> str:
    """Get an appropriate title for a multi-week calendar view.

    Args:
        calendar_grid: Calendar grid from generate_calendar_grid_weeks

    Returns:
        Formatted title string showing the date range

    """
    if not calendar_grid or not calendar_grid[0]:
        return "Calendar"

    start_date = calendar_grid[0][0]["date"]
    end_date = calendar_grid[-1][-1]["date"]

    if start_date.month == end_date.month:
        return start_date.strftime("%b %Y")
    if start_date.year == end_date.year:
        return f"{start_date.strftime('%b')} - {end_date.strftime('%b %Y')}"
    return f"{start_date.strftime('%b %Y')} - {end_date.strftime('%b %Y')}"


def is_event_multi_day(start_date: datetime.date, end_date: datetime.date) -> bool:
    """Check if an event spans multiple days.

    Args:
        start_date: Event start date
        end_date: Event end date

    Returns:
        True if the event spans multiple days

    """
    return start_date != end_date


def get_event_duration_hours(
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
) -> float:
    """Get event duration in hours.

    Args:
        start_datetime: Event start datetime
        end_datetime: Event end datetime

    Returns:
        Duration in hours

    """
    duration = end_datetime - start_datetime
    return duration.total_seconds() / 3600


def create_event_tooltip(event: CalendarEvent) -> str:
    """Create a detailed tooltip for an event.

    Args:
        event: Calendar event

    Returns:
        Formatted tooltip string

    """
    try:
        start_str = event.start_datetime.strftime("%a %b %d, %Y")
        end_str = event.end_datetime.strftime("%a %b %d, %Y")

        if event.is_all_day:
            # Use date() to avoid timezone comparison issues
            if event.start_datetime.date() == event.end_datetime.date():
                time_str = f"{start_str} (All day)"
            else:
                time_str = f"{start_str} - {end_str} (All day)"
        else:
            start_time = event.start_datetime.strftime("%I:%M %p")
            end_time = event.end_datetime.strftime("%I:%M %p")

            # Use date() to avoid timezone comparison issues
            if event.start_datetime.date() == event.end_datetime.date():
                time_str = f"{start_str} {start_time} - {end_time}"
            else:
                time_str = f"{start_str} {start_time} - {end_str} {end_time}"

        return f"{event.title}\n{time_str}"

    except (AttributeError, TypeError):
        # Fallback if there are any datetime issues
        return f"{event.title}\n(Time information unavailable)"


def get_spanning_events_for_date_range(
    events: list[CalendarEvent],
    start_date: datetime.date,
    end_date: datetime.date,
) -> list[CalendarEvent]:
    """Get events that span across the entire date range.

    Args:
        events: List of processed calendar events
        start_date: Start of the date range
        end_date: End of the date range

    Returns:
        List of events that span from start_date to end_date (or beyond)

    """
    return [
        event
        for event in events
        if event.start_datetime.date() <= start_date
        and event.end_datetime.date() >= end_date
    ]


def filter_events_not_in_list(
    all_events: list[CalendarEvent],
    exclude_events: list[CalendarEvent],
) -> list[CalendarEvent]:
    """Filter out events that are in the exclude list.

    Args:
        all_events: List of all events
        exclude_events: List of events to exclude

    Returns:
        List of events not in the exclude list

    """
    exclude_set = {event.id for event in exclude_events}
    return [event for event in all_events if event.id not in exclude_set]
