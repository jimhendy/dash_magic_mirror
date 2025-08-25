"""Rendering functions for Google Calendar component.

Contains all the visual rendering logic for calendar grids, events,
and detailed views, separated for better maintainability.
"""

import datetime
from calendar import day_name
from typing import Any

from dash import html

from utils.dates import (
    datetime_from_str,
)
from utils.styles import COLORS

from .utils import (
    generate_calendar_grid,
    get_corrected_end_date,
    process_multi_day_events,
)


class GoogleCalendarRenderer:
    """Handles all rendering logic for the Google Calendar component.

    Separated from callbacks and utility functions to keep
    visual rendering logic organized and maintainable.
    """

    def __init__(self, component_id: str):
        """Initialize the renderer.

        Args:
            component_id: Component identifier for consistent styling

        """
        self.component_id = component_id

    def render_calendar_month(
        self,
        year: int,
        month: int,
        events: list[dict[str, Any]],
    ) -> html.Div:
        """Render a focused calendar showing only relevant weeks with enhanced multi-day events.

        Args:
            year: Target year
            month: Target month
            events: List of event dictionaries

        Returns:
            Complete calendar month component

        """
        calendar_grid = generate_calendar_grid(year, month, events)
        event_spans = process_multi_day_events(calendar_grid, events)

        # Get the date range for the title
        if calendar_grid:
            start_date = calendar_grid[0][0]["date"]
            end_date = calendar_grid[-1][-1]["date"]
            if start_date.month == end_date.month:
                title = start_date.strftime("%B %Y")
            else:
                title = f"{start_date.strftime('%b')} - {end_date.strftime('%b %Y')}"
        else:
            title = datetime.date(year, month, 1).strftime("%B %Y")

        # Days of week header
        days_header = html.Div(
            [
                html.Div(
                    day_name[i][:3],  # Mon, Tue, etc.
                    style={
                        "flex": "1",
                        "textAlign": "center",
                        "fontWeight": "bold",
                        "padding": "8px",
                        "fontSize": "0.9rem",
                        "color": COLORS["soft_gray"],
                    },
                )
                for i in range(7)  # Monday to Sunday
            ],
            style={
                "display": "flex",
                "borderBottom": f"1px solid {COLORS['gray']}",
                "marginBottom": "4px",
            },
        )

        # Calendar weeks
        week_rows = []
        for week_idx, week in enumerate(calendar_grid):
            # Create the week container with relative positioning for spanning events
            week_container_style = {
                "position": "relative",
                "display": "flex",
                "minHeight": "100px",
            }

            week_cells = []
            week_multiday_events = []  # Events that span across this week

            # Track multi-day events for this week
            rendered_multiday_events = set()

            for day_idx, day_info in enumerate(week):
                date = day_info["date"]
                is_current_month = day_info["is_current_month"]
                is_today_cell = day_info["is_today"]
                is_past = day_info["is_past"]
                day_events = day_info["events"]

                # Day number styling
                day_number_style = {
                    "fontSize": "0.9rem",
                    "fontWeight": "bold" if is_today_cell else "normal",
                    "color": COLORS["white"] if not is_past else COLORS["gray"],
                    "marginBottom": "2px",
                    "position": "relative",
                    "zIndex": "20",
                }

                if is_today_cell:
                    day_number_style.update(
                        {
                            "background": COLORS["gold"],
                            "borderRadius": "50%",
                            "width": "20px",
                            "height": "20px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "color": COLORS["dark_gray"],
                        },
                    )

                # Event elements for single-day events only
                single_day_events = []
                event_y_position = 30  # Start below potential multi-day events

                # Collect multi-day events that start on this day
                for span_id, span_info in event_spans.items():
                    if (
                        span_info["week_index"] == week_idx
                        and span_info["start_day"] == day_idx
                        and span_id not in rendered_multiday_events
                    ):
                        week_multiday_events.append(span_info)
                        rendered_multiday_events.add(span_id)
                        rendered_multiday_events.add(span_info["event_id"])

                # Render single-day events for this day
                for event in day_events:
                    if event["id"] not in rendered_multiday_events:
                        # Verify this is actually a single-day event
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

                        # Only render if it's truly a single-day event
                        if start_date.date() == end_date.date():
                            event_element = self._render_single_day_event(
                                event,
                                event_y_position,
                            )
                            single_day_events.append(event_element)
                            event_y_position += 20

                # Limit single-day events to avoid overcrowding
                if len(single_day_events) > 3:
                    single_day_events = single_day_events[:3]
                    remaining_count = (
                        len(
                            [
                                e
                                for e in day_events
                                if e["id"] not in rendered_multiday_events
                            ],
                        )
                        - 3
                    )
                    if remaining_count > 0:
                        single_day_events.append(
                            html.Div(
                                f"+{remaining_count}",
                                style={
                                    "fontSize": "0.6rem",
                                    "color": COLORS["soft_gray"],
                                    "position": "absolute",
                                    "top": f"{event_y_position}px",
                                    "left": "4px",
                                    "zIndex": "15",
                                },
                            ),
                        )

                # Create day cell
                week_cells.append(
                    html.Div(
                        [
                            html.Div(
                                str(date.day),
                                style=day_number_style,
                            ),
                            *single_day_events,
                        ],
                        style={
                            "flex": "1",
                            "minHeight": "100px",
                            "padding": "4px",
                            "border": "1px solid rgba(255,255,255,0.1)",
                            "background": "rgba(255,255,255,0.02)"
                            if is_current_month
                            else "rgba(255,255,255,0.005)",
                            "position": "relative",
                            "opacity": "0.6" if is_past else "1.0",
                        },
                    ),
                )

            # Create multi-day event overlays for this week
            multiday_overlays = []
            for i, span_info in enumerate(week_multiday_events):
                overlay = self._render_week_spanning_event(
                    span_info,
                    i * 22 + 25,
                )  # Stack multi-day events
                multiday_overlays.append(overlay)

            # Combine the week row with day cells and multi-day overlays
            week_row = html.Div(
                [
                    html.Div(week_cells, style={"display": "flex", "width": "100%"}),
                    *multiday_overlays,
                ],
                style=week_container_style,
            )
            week_rows.append(week_row)

        return html.Div(
            [
                html.H3(
                    title,
                    style={
                        "textAlign": "center",
                        "color": COLORS["white"],
                        "marginBottom": "16px",
                        "fontSize": "1.4rem",
                    },
                ),
                days_header,
                html.Div(week_rows),
            ],
            style={
                "marginBottom": "32px",
                "border": "1px solid rgba(255,255,255,0.1)",
                "borderRadius": "8px",
                "padding": "16px",
                "background": "rgba(255,255,255,0.02)",
            },
        )

    def _render_single_day_event(
        self,
        event: dict[str, Any],
        y_position: int,
    ) -> html.Div:
        """Render a single day event with title and time.

        Args:
            event: Event dictionary
            y_position: Vertical position for the event

        Returns:
            Single day event component

        """
        start_time = None
        if event["start"].get("dateTime"):
            start_date = datetime_from_str(event["start"]["dateTime"], is_all_day=False)
            start_time = start_date.strftime("%H:%M")

        title = event.get("summary", "No Title")
        # Allow more text since we have more space
        if len(title) > 20:
            title = title[:17] + "..."

        # Check if it's a birthday for color
        is_birthday = "birthday" in title.lower() or "🎂" in title

        # Use better colors with dark text for readability
        if is_birthday:
            bg_color = COLORS["gold"]  # Gold/yellow background
            text_color = COLORS["dark_gray"]  # Dark text
            time_color = COLORS["gray"]  # Darker gray for time
        else:
            bg_color = COLORS["green"]  # Green background
            text_color = COLORS["dark_gray"]  # Dark text
            time_color = COLORS["gray"]  # Darker gray for time

        return html.Div(
            [
                html.Div(
                    title,
                    style={
                        "fontSize": "0.75rem",  # Slightly larger
                        "fontWeight": "600",
                        "color": text_color,
                        "lineHeight": "1.2",
                        "marginBottom": "2px",  # More space
                    },
                ),
                html.Div(
                    start_time or "All day",
                    style={
                        "fontSize": "0.65rem",  # Slightly larger
                        "color": time_color,
                        "lineHeight": "1.0",
                    },
                )
                if start_time
                else None,
            ],
            style={
                "position": "absolute",
                "top": f"{y_position + 25}px",
                "left": "2px",
                "right": "2px",
                "backgroundColor": bg_color,
                "borderRadius": "4px",  # Slightly more rounded
                "padding": "4px 6px",  # More padding for better spacing
                "fontSize": "0.65rem",
                "height": "28px",  # Increased from 16px to 28px for more space
                "overflow": "hidden",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.3)",
                "border": "1px solid rgba(0,0,0,0.1)",  # Subtle dark border
                "zIndex": "10",
            },
        )

    def _render_week_spanning_event(
        self,
        span_info: dict[str, Any],
        y_position: int,
    ) -> html.Div:
        """Render a multi-day event that spans across multiple day cells.

        Args:
            span_info: Event span information dictionary
            y_position: Vertical position for the event

        Returns:
            Week spanning event component

        """
        event = span_info["event"]
        start_day = span_info["start_day"]
        end_day = span_info["end_day"]
        is_first_week = span_info["is_first_week"]
        is_last_week = span_info["is_last_week"]
        spans_multiple_weeks = span_info["spans_multiple_weeks"]

        title = event.get("summary", "No Title")
        # Don't truncate as much since we have more space
        if len(title) > 35:
            title = title[:32] + "..."

        # Calculate position and width to span across multiple day cells
        # Each day is 1/7 of the week width
        left_percentage = (start_day / 7) * 100
        width_percentage = ((end_day - start_day + 1) / 7) * 100

        # Determine border radius based on continuation state
        if not spans_multiple_weeks:
            # Single week event - both ends curved
            border_radius = "8px"
        elif is_first_week and not is_last_week:
            # First week of multi-week event - curved start, square end
            border_radius = "8px 2px 2px 8px"
        elif not is_first_week and is_last_week:
            # Last week of multi-week event - square start, curved end
            border_radius = "2px 8px 8px 2px"
        else:
            # Middle week of multi-week event - square both ends
            border_radius = "2px"

        # Check if it's a birthday for color
        is_birthday = "birthday" in title.lower() or "🎂" in title

        # Use better colors with dark text for better readability
        if is_birthday:
            bg_color = COLORS["gold"]  # Gold/yellow background
            text_color = COLORS["dark_gray"]  # Dark text
        else:
            bg_color = COLORS["green"]  # Green background
            text_color = COLORS["dark_gray"]  # Dark text

        return html.Div(
            title,
            style={
                "position": "absolute",
                "top": f"{y_position}px",
                "left": f"{left_percentage}%",
                "width": f"{width_percentage}%",
                "height": "26px",  # Increased from 18px to 26px for more space
                "backgroundColor": bg_color,
                "borderRadius": border_radius,
                "padding": "4px 10px",  # Increased padding for better text spacing
                "fontSize": "0.8rem",  # Slightly larger font
                "fontWeight": "600",
                "color": text_color,
                "lineHeight": "18px",  # Better line height for the increased height
                "overflow": "hidden",
                "whiteSpace": "nowrap",
                "textOverflow": "ellipsis",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.3)",
                "zIndex": "25",  # Higher than day cells
                "border": "1px solid rgba(0,0,0,0.1)",  # Subtle dark border
                "display": "flex",
                "alignItems": "center",
            },
        )
