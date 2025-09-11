"""Google Calendar component for the Magic Mirror application.

Displays today and tomorrow's events in a calendar-like layout.
Uses Google Calendar API for event data.
"""

from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent, PreloadedFullScreenMixin

from .data import fetch_calendar_events, process_calendar_events


class GoogleCalendar(PreloadedFullScreenMixin, BaseComponent):
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
        # Enable preloaded full screen path
        super().__init__(name="google_calendar", preloaded_full_screen=True, **kwargs)
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
            raw_events,
            truncate_to_tomorrow=truncate_to_tomorrow,
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
                *self.preload_fullscreen_stores(),
                html.Div(
                    id=f"{self.component_id}-content",
                    style={
                        "color": "#FFFFFF",
                        "fontSize": "14px",
                        # inherit font
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

        # Populate full screen stores (separate processing without truncation)
        @app.callback(
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval", "n_intervals"),
            prevent_initial_call=False,
        )
        def populate_fullscreen(_n):
            try:
                from .full_screen import render_calendar_fullscreen

                processed_events = self._get_processed_events(
                    truncate_to_tomorrow=False,
                )
                fs_result = render_calendar_fullscreen(processed_events)
                title = html.Div(
                    fs_result.title,
                    className="text-m",
                    **{"data-component-name": self.name},
                )
                return title, fs_result.content
            except Exception as e:
                logger.error(f"Error preparing calendar full screen: {e}")
                return None, None
