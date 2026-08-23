"""Google Calendar component for the Magic Mirror application.

Displays today and tomorrow's events in a calendar-like layout.
Uses Google Calendar API for event data.
"""

from dash import html
from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload

from .data import async_fetch_calendar_events, process_calendar_events


class GoogleCalendar(DataDrivenComponent):
    """Google Calendar component for the Magic Mirror application.

    Displays today and tomorrow's events in a two-day calendar view.
    Shows event timing, duration, and continuation status with visual indicators.

    Uses Google Calendar API for event data.
    Requires Google Calendar API credentials file.
    """

    refresh_seconds = 5 * 60
    jitter_seconds = 30
    placeholder_error = "Calendar unavailable"
    placeholder_loading = "Loading calendar..."

    def __init__(self, calendar_ids: list[str], **kwargs):
        """Initialize Google Calendar component.

        Args:
            calendar_ids: Google Calendar IDs to fetch events from.

        """
        self.calendar_ids = calendar_ids
        super().__init__(name="google_calendar", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        """Fetch and render calendar data asynchronously."""
        raw_events = await async_fetch_calendar_events(self.calendar_ids)
        summary_events = process_calendar_events(
            raw_events,
            truncate_to_tomorrow=True,
        )
        fullscreen_events = process_calendar_events(
            raw_events,
            truncate_to_tomorrow=False,
        )

        try:
            from .full_screen import render_calendar_fullscreen
            from .summary import render_calendar_summary

            summary_children = render_calendar_summary(summary_events)
            fullscreen_result = render_calendar_fullscreen(fullscreen_events)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering calendar payload")
            return ComponentPayload(
                summary=self._build_placeholder(self.placeholder_error),
            )

        title = html.Div(
            fullscreen_result.title,
            className="text-m",
            **{"data-component-name": self.name},
        )

        return ComponentPayload(
            summary=summary_children,
            fullscreen_title=title,
            fullscreen_content=fullscreen_result.content,
            raw={"events": fullscreen_events},
        )
