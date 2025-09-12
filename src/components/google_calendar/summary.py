"""Summary view rendering for Google Calendar component."""

import datetime

from dash import html

from utils.calendar import get_event_color_by_event, truncate_event_title
from utils.dates import local_today
from utils.styles import FONT_SIZES

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

    def _render_multi_day_event(event):
        event_starts_here = event.start_datetime.date() == today
        event_ends_here = event.end_datetime.date() == tomorrow
        border_radius = calculate_event_border_radius(
            event_starts_here,
            event_ends_here,
        )
        margin_left, margin_right = calculate_event_margins(
            event_starts_here,
            event_ends_here,
        )
        event_styles = get_common_event_styles()
        accent_color = get_event_color_by_event(event.id)
        event_styles.update(
            {
                # Neutral background; color only on border
                "background": "rgba(255,255,255,0.04)",
                "border": f"3px solid {accent_color}",
                "borderRadius": border_radius,
                "marginLeft": "auto",
                "marginRight": "auto",
                "position": "relative",
                "width": "97%",
            },
        )
        time_display = generate_event_time_display(
            event,
            event_starts_here,
            event_ends_here,
        )
        return html.Div(
            style=event_styles,
            children=[
                html.Div(
                    truncate_event_title(event.title, 40),
                    style={
                        "fontWeight": "350",
                        "marginBottom": "2px" if time_display else "0px",
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                        "fontSize": "1.3rem",
                    },
                ),
                html.Div(
                    time_display,
                    style={
                        "opacity": "0.9",
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                        "fontSize": FONT_SIZES["summary_meta"],
                    },
                )
                if time_display
                else None,
            ],
        )

    return html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "width": "100%",
            "gap": "8px",
            "cursor": "pointer",
            "alignItems": "stretch",
            # inherit font
            "fontSize": FONT_SIZES["summary_secondary"],
        },
        children=[
            *[_render_multi_day_event(event) for event in multi_day_events],
            html.Div(
                style={
                    "display": "flex",
                    "gap": "8px",
                },
                children=[
                    _render_day_column(today, single_today_events, "Today"),
                    _render_day_column(tomorrow, single_tomorrow_events, "Tomorrow"),
                ],
            ),
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
            "paddingTop": "4px",
        },
        children=[
            # Events container
            html.Div(
                style={
                    "flex": "1",
                    "padding": "4px 6px 8px 6px",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "4px",
                },
                children=[_render_event(event, date) for event in events],
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

    border_radius = calculate_event_border_radius(
        event_starts_here,
        event_ends_here,
    )
    margin_left, margin_right = calculate_event_margins(
        event_starts_here,
        event_ends_here,
    )

    accent_color = get_event_color_by_event(event.id)

    time_display = generate_event_time_display(
        event,
        event_starts_here,
        event_ends_here,
    )

    return html.Div(
        style={
            "padding": "6px 8px 6px 10px",
            "fontSize": FONT_SIZES["summary_meta"],
            "lineHeight": "1.15",
            "fontWeight": "350",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "whiteSpace": "nowrap",
            "borderRadius": border_radius,
            "marginLeft": margin_left,
            "marginRight": margin_right,
            "position": "relative",
            "background": "rgba(255,255,255,0.04)",
            "border": f"3px solid {accent_color}",
            "display": "flex",
            "flexDirection": "column",
        },
        children=[
            html.Div(
                truncate_event_title(event.title, 40),
                style={
                    "fontWeight": "350",
                    "marginBottom": "1px" if time_display else "0px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                    "fontSize": "1.3rem",
                },
            ),
            html.Div(
                time_display,
                style={
                    "fontSize": FONT_SIZES["summary_small"],
                    "opacity": 0.85,
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                    "whiteSpace": "nowrap",
                },
            )
            if time_display
            else None,
        ],
    )
