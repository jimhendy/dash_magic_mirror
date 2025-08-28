"""Google Calendar component for the Magic Mirror application.

Displays today and tomorrow's events in a calendar-like layout.
Uses Google Calendar API for event data.
"""

from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.models import FullScreenResult

from .data import fetch_calendar_events, process_calendar_events


class GoogleCalendar(BaseComponent):
    """Google Calendar component for the Magic Mirror application.

    Displays today and tomorrow's events in a two-day calendar view.
    Shows event timing, duration, and continuation status with visual indicators.

    Uses Google Calendar API for event data.
    Requires Google Calendar API credentials file.
    """

    def __init__(self, calendar_ids: list[str], **kwargs):
        """Initialize Google Calendar component.

        Args:
            calendar_config: Configuration object with calendar IDs and settings

        """
        super().__init__(name="google_calendar", **kwargs)
        self.calendar_ids = calendar_ids

    def _get_processed_events(self, truncate_to_tomorrow: bool = True):
        """Get processed calendar events with error handling.

        Args:
            truncate_to_tomorrow: Whether to truncate events to tomorrow

        Returns:
            List of processed CalendarEvent objects

        Raises:
            Exception: If there's an error fetching or processing events

        """
        raw_events = fetch_calendar_events(self.calendar_ids)
        return process_calendar_events(
            raw_events, truncate_to_tomorrow=truncate_to_tomorrow,
        )

    def _summary_layout(self):
        """Returns the layout of the Google Calendar component."""
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=5 * 60 * 1000,  # Update every 5 minutes
                    n_intervals=0,
                ),
                html.Div(
                    id=f"{self.component_id}-content",
                    style={
                        "color": "#FFFFFF",
                        "fontSize": "14px",
                        "fontFamily": "'Inter', 'Roboto', 'Segoe UI', 'Helvetica Neue', sans-serif",
                        "width": "100%",
                    },
                ),
            ],
        )

    def _add_callbacks(self, app):
        """Add callbacks for the Google Calendar component."""

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Input(f"{self.component_id}-interval", "n_intervals"),
        )
        def update_calendar(_):
            try:
                from .summary import render_calendar_summary

                processed_events = self._get_processed_events(truncate_to_tomorrow=True)
                return render_calendar_summary(processed_events)
            except Exception as e:
                logger.error(f"Error updating calendar: {e}")
                return html.Div("Calendar unavailable", style={"color": "#FF6B6B"})

    def full_screen_content(self) -> FullScreenResult:
        """Returns the full-screen layout of the Google Calendar component."""
        try:
            from .full_screen import render_calendar_fullscreen

            processed_events = self._get_processed_events(truncate_to_tomorrow=False)
            return render_calendar_fullscreen(processed_events)
        except Exception as e:
            logger.error(f"Error loading full-screen calendar: {e}")
            return FullScreenResult(
                content=html.Div(
                    "Calendar unavailable",
                    style={
                        "color": "#FF6B6B",
                        "textAlign": "center",
                        "padding": "2rem",
                        "fontSize": "1.5rem",
                    },
                ),
                title="Calendar Unavailable",
            )
