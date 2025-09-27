"""Full screen view rendering for Google Calendar component."""

import datetime
from calendar import day_name

from dash import html

from utils.calendar import (
    get_contrasting_text_color,
    get_event_color_by_event,
)
from utils.dates import local_today
from utils.models import FullScreenResult

from .data import CalendarEvent
from .utils import (
    create_event_spans,
    create_event_tooltip,
    generate_calendar_grid_weeks,
    get_calendar_title_for_weeks,
    prepare_events_for_rendering,
)


def render_calendar_fullscreen(
    events: list[CalendarEvent],
    font_size: str = "20px",
) -> FullScreenResult:
    """Render the full-screen calendar view showing 4 weeks in a grid.

    Args:
        events: List of processed calendar events
        font_size: Font size for the calendar text

    Returns:
        FullScreenResult containing the full-screen calendar layout

    """
    # Prepare events with consistent color assignment and sorting
    sorted_events = prepare_events_for_rendering(events)

    today = local_today()

    # Start from the beginning of the current week
    start_of_week = today - datetime.timedelta(days=today.weekday())

    # Generate 4 weeks of calendar grid
    calendar_grid = generate_calendar_grid_weeks(start_of_week, 4, sorted_events)
    calendar_title = get_calendar_title_for_weeks(calendar_grid)

    # Create event spans for multi-day event rendering
    event_spans = create_event_spans(calendar_grid)

    return FullScreenResult(
        content=_render_calendar_grid(calendar_grid, event_spans, font_size),
        title=calendar_title,
    )


def _render_calendar_grid(
    calendar_grid: list[list[dict]],
    event_spans: list[dict],
    font_size: str,
) -> html.Div:
    """Render the calendar grid with weeks and days.

    Args:
        calendar_grid: Calendar grid from generate_calendar_grid_weeks
        event_spans: Event spans from create_event_spans
        font_size: Font size for the calendar

    Returns:
        html.Div containing the calendar grid

    """
    return html.Div(
        style={
            "flex": "1",
            "display": "flex",
            "flexDirection": "column",
            "border": "1px solid rgba(255, 255, 255, 0.2)",
            "borderRadius": "12px",
            "backgroundColor": "rgba(255, 255, 255, 0.02)",
            "height": "100%",
            "position": "relative",
        },
        children=[
            # Days of week header
            _render_days_header(font_size=font_size),
            # Calendar weeks
            html.Div(
                style={
                    "flex": "1",
                    "display": "flex",
                    "flexDirection": "column",
                    "position": "relative",
                },
                children=[
                    _render_calendar_week(week, week_idx, font_size=font_size)
                    for week_idx, week in enumerate(calendar_grid)
                ]
                + [
                    # Render event spans as overlays
                    _render_event_spans(event_spans, font_size),
                ],
            ),
        ],
    )


def _render_days_header(font_size: str) -> html.Div:
    """Render the days of week header row.

    Args:
        font_size: Font size for the header

    Returns:
        html.Div containing the days header

    """
    return html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(7, 1fr)",
            "borderBottom": "1px solid rgba(255, 255, 255, 0.2)",
            "backgroundColor": "rgba(255, 255, 255, 0.05)",
        },
        children=[
            html.Div(
                day_name[i][:3],  # Mon, Tue, Wed, etc.
                style={
                    "padding": "12px",
                    "textAlign": "center",
                    "fontWeight": "bold",
                    "fontSize": "14px",  # Fixed size for header
                    "color": "rgba(255, 255, 255, 0.7)",
                },
            )
            for i in range(7)  # Monday to Sunday
        ],
    )


def _render_calendar_week(week: list[dict], week_idx: int, font_size: str) -> html.Div:
    """Render a single week row in the calendar.

    Args:
        week: Week data from calendar grid
        week_idx: Index of the week in the grid
        font_size: Font size for the calendar

    Returns:
        html.Div containing the week row

    """
    return html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(7, 1fr)",
            "borderBottom": "1px solid rgba(255, 255, 255, 0.1)",
            "height": "24%",
        },
        children=[_render_calendar_day(day_info, font_size) for day_info in week],
    )


def _render_calendar_day(day_info: dict, font_size: str) -> html.Div:
    """Render a single day cell in the calendar.

    Args:
        day_info: Day information from calendar grid
        font_size: Font size for the calendar

    Returns:
        html.Div containing the day cell

    """
    date = day_info["date"]
    is_today = day_info["is_today"]
    is_past = day_info["is_past"]

    # Check if it's a weekend (Saturday = 5, Sunday = 6)
    is_weekend = date.weekday() >= 5

    # Check if it's the first day of the month
    is_first_of_month = date.day == 1

    # Day cell background styling for weekends
    cell_style = {
        "padding": "8px",
        "borderRight": "1px solid rgba(255, 255, 255, 0.1)",
        "display": "flex",
        "flexDirection": "column",
        "position": "relative",
    }

    # Add subtle background for weekends
    if is_weekend:
        cell_style["backgroundColor"] = "rgba(255, 255, 255, 0.1)"

    # Day number styling
    day_number_style = {
        "fontSize": "16px",  # Fixed readable size for day numbers
        "fontWeight": "bold"
        if is_today
        else ("bold" if is_first_of_month else "normal"),
        "color": "#FFFFFF" if not is_past else "rgba(255, 255, 255, 0.4)",
        "marginBottom": "6px",
    }

    # Current day styling (most prominent)
    if is_today:
        day_number_style.update(
            {
                "backgroundColor": "#FFD700",
                "color": "#000000",
                "borderRadius": "50%",
                "width": "24px",
                "height": "24px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
            },
        )
    # First of month styling (less prominent than current day)
    elif is_first_of_month:
        day_number_style.update(
            {
                "border": "1px solid rgba(255, 255, 255, 0.4)",
                "borderRadius": "50%",
                "width": "22px",
                "height": "22px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "backgroundColor": "rgba(255, 255, 255, 0.05)",
            },
        )

    return html.Div(
        style=cell_style,
        children=[
            # Day number
            html.Div(
                str(date.day),
                style=day_number_style,
            ),
        ],
    )


def _render_event_spans(event_spans: list[dict], font_size: str) -> html.Div:
    """Render event spans as overlays on the calendar grid.

    Args:
        event_spans: List of event span dictionaries
        font_size: Font size for event text

    Returns:
        html.Div containing all event span overlays

    """
    return html.Div(
        style={
            "position": "absolute",
            "top": "0",
            "left": "0",
            "right": "0",
            "bottom": "0",
            "pointerEvents": "none",
        },
        children=[_render_single_event_span(span, font_size) for span in event_spans],
    )


def _render_single_event_span(event_span: dict, font_size: str) -> html.Div:
    """Render a single event span overlay.

    Args:
        event_span: Event span dictionary with positioning info
        font_size: Font size for event text

    Returns:
        html.Div containing the event span

    """
    event = event_span["event"]
    start_week = event_span["start_week"]
    start_day = event_span["start_day"]
    end_week = event_span["end_week"]
    end_day = event_span["end_day"]
    track = event_span.get("track", 0)  # Vertical position within week

    # Calculate positioning - improved calculations
    header_height = 60  # Account for header height
    week_height_percent = 24  # Each week is 24% of available height
    day_width_percent = 100 / 7  # Each day is 1/7 of width

    # Event color based on event ID for better distinction
    background_color = get_event_color_by_event(event.id)

    # Calculate contrasting text color
    text_color = get_contrasting_text_color(background_color)

    # Create tooltip with event details
    tooltip_text = create_event_tooltip(event)

    # Calculate event height and font size based on input font size
    event_height = 22
    event_font_size = "12px"
    event_margin = 4  # Space between stacked events
    base_offset = 1  # distance from top of day cell to first event
    track_spacing = event_height + event_margin

    # For multi-week events, we need to create multiple spans
    event_segments = []

    def _top_position(week_index: int) -> str:
        offset_px = base_offset + (track - 1) * track_spacing
        return (
            f"calc({header_height}px + {week_height_percent}% * {week_index} + {offset_px}px)"
        )

    if start_week == end_week:
        # Same week - single span
        # Add offset for curved ends
        left_offset = 4 if start_day > 0 else 0  # Offset from left edge
        right_offset = 4 if end_day < 6 else 0  # Offset from right edge

        left_pos = f"calc({day_width_percent * start_day}% + {left_offset}px)"
        width = f"calc({day_width_percent * (end_day - start_day + 1)}% - {left_offset + right_offset}px)"
        top_pos = _top_position(start_week)

        event_segments.append(
            html.Div(
                event.title,
                title=tooltip_text,
                style={
                    "position": "absolute",
                    "left": left_pos,
                    "width": width,
                    "top": top_pos,
                    "height": f"{event_height}px",
                    "backgroundColor": background_color,
                    "borderRadius": "4px",
                    "padding": "3px 8px",
                    "fontSize": event_font_size,
                    "fontWeight": "600",
                    "lineHeight": f"{event_height - 6}px",
                    "color": text_color,
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                    "pointerEvents": "auto",
                    "cursor": "default",
                    "zIndex": f"{10 + track}",
                    "boxShadow": "0 1px 3px rgba(0, 0, 0, 0.3)",
                },
            ),
        )
    else:
        # Multi-week event - create segments for each week
        for week in range(start_week, end_week + 1):
            if week == start_week:
                # First week segment - offset from left if not starting at beginning
                left_offset = 4 if start_day > 0 else 0
                left_pos = f"calc({day_width_percent * start_day}% + {left_offset}px)"
                width = (
                    f"calc({day_width_percent * (7 - start_day)}% - {left_offset}px)"
                )
                show_title = True  # Always show title on first week
                border_radius = "4px 0 0 4px"
            elif week == end_week:
                # Last week segment - offset from right if not ending at end
                right_offset = 4 if end_day < 6 else 0
                left_pos = "0%"
                width = f"calc({day_width_percent * (end_day + 1)}% - {right_offset}px)"
                show_title = True  # Show title on new row (last week)
                border_radius = "0 4px 4px 0"
            else:
                # Middle week segment
                left_pos = "0%"
                width = "100%"
                show_title = True  # Show title on new row (middle weeks)
                border_radius = "0"

            top_pos = _top_position(week)

            event_segments.append(
                html.Div(
                    event.title if show_title else "",
                    title=tooltip_text,
                    style={
                        "position": "absolute",
                        "left": left_pos,
                        "width": width,
                        "top": top_pos,
                        "height": f"{event_height}px",
                        "backgroundColor": background_color,
                        "borderRadius": border_radius,
                        "padding": "3px 8px",
                        "fontSize": event_font_size,
                        "fontWeight": "600",
                        "lineHeight": f"{event_height - 6}px",
                        "color": text_color,
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                        "pointerEvents": "auto",
                        "cursor": "default",
                        "zIndex": f"{10 + track}",
                        "boxShadow": "0 1px 3px rgba(0, 0, 0, 0.3)",
                    },
                ),
            )

    return html.Div(children=event_segments)
