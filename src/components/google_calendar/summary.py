"""Summary view rendering for Google Calendar component."""

import datetime

from dash import html

from utils.calendar import get_event_color_by_calendar, truncate_event_title

from .data import CalendarEvent, get_events_for_date


def render_calendar_summary(events: list[CalendarEvent]) -> html.Div:
    """Render the calendar summary view showing today and tomorrow.

    Args:
        events: List of processed calendar events

    Returns:
        html.Div containing the calendar summary layout

    """
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    today_events = get_events_for_date(events, today)
    tomorrow_events = get_events_for_date(events, tomorrow)

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
                    html.Div(label),
                    html.Div(
                        date.strftime("%d %b"),
                        style={
                            "fontSize": "12px",
                            "opacity": "0.8",
                            "marginTop": "2px",
                        },
                    ),
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
    event_starts_on_display_date = event.start_datetime.date() == display_date
    event_ends_on_display_date = event.end_datetime.date() == display_date

    # Calculate border radius based on event continuation
    border_radius_left = "8px" if event_starts_on_display_date else "0px"
    border_radius_right = "8px" if event_ends_on_display_date else "0px"

    # Calculate margins based on event continuation - move curved edges away from column edges
    margin_left = "4px" if event_starts_on_display_date else "-8px"
    margin_right = "4px" if event_ends_on_display_date else "-8px"

    # Event color based on calendar
    background_color = get_event_color_by_calendar(event.calendar_id)

    # Time display
    time_display = ""
    if not event.is_all_day:
        if event_starts_on_display_date and event_ends_on_display_date:
            # Same day event
            time_display = f"{event.start_datetime.strftime('%H:%M')} - {event.end_datetime.strftime('%H:%M')}"
        elif event_starts_on_display_date:
            # Starts today, continues
            time_display = f"From {event.start_datetime.strftime('%H:%M')}"
        elif event_ends_on_display_date:
            # Ends today
            time_display = f"Until {event.end_datetime.strftime('%H:%M')}"
        else:
            # Continues all day
            time_display = "All day"

    return html.Div(
        style={
            "backgroundColor": background_color,
            "padding": "6px 8px",
            "borderRadius": f"{border_radius_left} {border_radius_right} {border_radius_right} {border_radius_left}",
            "marginLeft": margin_left,
            "marginRight": margin_right,
            "fontSize": "12px",
            "lineHeight": "1.2",
            "position": "relative",
        },
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
