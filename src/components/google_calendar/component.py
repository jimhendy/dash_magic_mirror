"""Google Calendar component for the Magic Mirror application.

Tile: today, tomorrow and the rest of the week. Panel: a day-by-day agenda for the
coming weeks. Uses the Google Calendar API for event data.
"""

from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload
from utils.styles import CALENDAR_PALETTE, COLORS

from .data import async_fetch_calendar_events, process_calendar_events
from .full_screen import render_calendar_fullscreen
from .summary import render_calendar_badge, render_calendar_summary


class GoogleCalendar(DataDrivenComponent):
    """Requires a Google Calendar API credentials file (see README)."""

    title = "Calendar"
    icon = "mdi:calendar-month-outline"
    accent = COLORS["blue"]
    refresh_seconds = 5 * 60
    jitter_seconds = 30
    placeholder_error = "Calendar unavailable"
    placeholder_loading = "Loading calendar…"

    def __init__(self, calendar_ids: list[str], **kwargs):
        """Initialize Google Calendar component.

        Args:
            calendar_ids: Google Calendar IDs to fetch events from. Their
                order decides each calendar's colour.

        """
        self.calendar_ids = calendar_ids
        self.colors = {
            cal_id: CALENDAR_PALETTE[i % len(CALENDAR_PALETTE)]
            for i, cal_id in enumerate(calendar_ids)
        }
        super().__init__(name="google_calendar", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        raw_events = await async_fetch_calendar_events(self.calendar_ids)
        events = process_calendar_events(raw_events, truncate_to_tomorrow=False)

        try:
            summary = render_calendar_summary(events, self.colors)
            detail = render_calendar_fullscreen(events, self.colors)
            badge = render_calendar_badge(events)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering calendar payload")
            return None

        return ComponentPayload(
            summary=summary,
            detail=detail,
            subtitle="Upcoming events",
            badge=badge,
            raw={"events": events},
        )
