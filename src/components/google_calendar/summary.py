"""Summary view rendering for Google Calendar component."""

import datetime

from dash import html

from utils.calendar import get_event_color_by_event, truncate_event_title

from .data import CalendarEvent, get_events_for_date
from .utils import (
    calculate_event_border_radius,
    calculate_event_margins,
    generate_event_time_display,
    get_common_event_styles,
    prepare_events_for_rendering,
)


def render_calendar_summary(events: list[CalendarEvent]) -> html.Div:
    """Render the calendar summary view showing today and tomorrow.

    Args:
        events: List of processed calendar events

    Returns:
        html.Div containing the calendar summary layout

    """
    # Prepare events with consistent color assignment and sorting
    sorted_events = prepare_events_for_rendering(events)

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    today_events = get_events_for_date(sorted_events, today)
    tomorrow_events = get_events_for_date(sorted_events, tomorrow)

    return html.Div(
        style={
            "display": "flex",
            "width": "100%",
            "gap": "8px",
            "cursor": "pointer",
        },
        children=[
            _render_day_column(today, today_events, "Today"),
            _render_day_column(tomorrow, tomorrow_events, "Tomorrow"),
        ],
    )


def _render_day_column(
    date: datetime.date,
    events: list[CalendarEvent],
    label: str,
) -> html.Div:
    """Render a single day column with calendar appearance.

    Args:
        date: Date for this column
        events: Events occurring on this date
        label: Display label for the day

    Returns:
        html.Div containing the day column

    """
    return html.Div(
        style={
            "flex": "1",
            "display": "flex",
            "flexDirection": "column",
            "border": "1px solid rgba(255, 255, 255, 0.2)",
            "borderRadius": "8px",
            "minHeight": "200px",
            "backgroundColor": "rgba(255, 255, 255, 0.05)",
        },
        children=[
            # Day header
            html.Div(
                style={
                    "padding": "8px 12px",
                    "backgroundColor": "rgba(255, 255, 255, 0.1)",
                    "borderRadius": "8px 8px 0 0",
                    "borderBottom": "1px solid rgba(255, 255, 255, 0.2)",
                    "textAlign": "center",
                    "fontWeight": "bold",
                    "fontSize": "16px",
                },
                children=[
                    html.Div(f"{label}, {date.strftime('%d %b')}")
                ],
            ),
            # Events container
            html.Div(
                style={
                    "flex": "1",
                    "padding": "8px",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "4px",
                },
                children=[_render_event(event, date) for event in events]
                or [
                    html.Div(
                        "No events",
                        style={
                            "textAlign": "center",
                            "opacity": "0.5",
                            "fontSize": "12px",
                            "marginTop": "20px",
                        },
                    ),
                ],
            ),
        ],
    )


def _render_event(event: CalendarEvent, display_date: datetime.date) -> html.Div:
    """Render a single event with appropriate styling.

    Args:
        event: Calendar event to render
        display_date: Date being displayed (for edge styling)

    Returns:
        html.Div containing the event

    """
    # Determine event position and styling
    event_starts_here = event.start_datetime.date() == display_date
    event_ends_here = event.end_datetime.date() == display_date

    # Use common utility functions for styling
    border_radius = calculate_event_border_radius(event_starts_here, event_ends_here)
    margin_left, margin_right = calculate_event_margins(
        event_starts_here,
        event_ends_here,
    )

    # Get base event styles and customize for summary view
    event_styles = get_common_event_styles()
    event_styles.update(
        {
            "backgroundColor": get_event_color_by_event(event.id),
            "borderRadius": border_radius,
            "marginLeft": margin_left,
            "marginRight": margin_right,
            "position": "relative",
        },
    )

    # Generate time display using common utility
    time_display = generate_event_time_display(
        event,
        event_starts_here,
        event_ends_here,
    )

    return html.Div(
        style=event_styles,
        children=[
            html.Div(
                truncate_event_title(event.title, 25),
                style={
                    "fontWeight": "500",
                    "marginBottom": "2px" if time_display else "0px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                },
            ),
            html.Div(
                time_display,
                style={
                    "fontSize": "10px",
                    "opacity": "0.9",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                },
            )
            if time_display
            else None,
        ],
    )
