"""Google Calendar component for the Magic Mirror application.

Displays today and tomorrow's events in a calendar-like layout.
Uses Google Calendar API for event data.
"""

import datetime

from dash import html
from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload
from utils.dates import local_today

from .data import CalendarEvent, async_fetch_calendar_events, process_calendar_events


class GoogleCalendar(DataDrivenComponent):
    """Google Calendar component for the Magic Mirror application.

    Displays today and tomorrow's events in a two-day calendar view.
    Shows event timing, duration, and continuation status with visual indicators.

    Uses Google Calendar API for event data.
    Requires Google Calendar API credentials file.

    Optionally overlays bin-collection dates (scraped from the council's own
    site, see `components.bin_collection`) onto the same view - this is
    presentation only, nothing is written back to the underlying Google
    Calendar.
    """

    refresh_seconds = 5 * 60
    jitter_seconds = 30
    placeholder_error = "Calendar unavailable"
    placeholder_loading = "Loading calendar..."

    def __init__(
        self,
        calendar_ids: list[str],
        *,
        bin_collection_postcode: str = "",
        bin_collection_address: str = "",
        **kwargs,
    ):
        """Initialize Google Calendar component.

        Args:
            calendar_ids: Google Calendar IDs to fetch events from.
            bin_collection_postcode: Postcode used to look up bin collection
                dates. Leave blank to skip the bin-collection overlay.
            bin_collection_address: The exact address text (as shown in the
                council's address picker) to select for the bin lookup.

        """
        self.calendar_ids = calendar_ids
        self.bin_collection_postcode = bin_collection_postcode
        self.bin_collection_address = bin_collection_address
        super().__init__(name="google_calendar", **kwargs)

    async def _fetch_bin_collection_events(self) -> list[CalendarEvent]:
        if not self.bin_collection_postcode or not self.bin_collection_address:
            return []
        try:
            # Imported lazily to avoid a circular import: `bin_collection`
            # builds `CalendarEvent` objects, so it imports from
            # `google_calendar.data` - a module-level import here would
            # form a cycle back to this file.
            from components.bin_collection import (
                async_fetch_bin_collections,
                build_bin_collection_events,
            )

            entries = await async_fetch_bin_collections(
                self.bin_collection_postcode,
                self.bin_collection_address,
            )
            return build_bin_collection_events(entries)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to fetch bin collection dates")
            return []

    async def _build_payload(self) -> ComponentPayload | None:
        """Fetch and render calendar data asynchronously."""
        raw_events = await async_fetch_calendar_events(self.calendar_ids)
        bin_events = await self._fetch_bin_collection_events()

        today = local_today()
        tomorrow = today + datetime.timedelta(days=1)
        summary_bin_events = [
            e for e in bin_events if e.start_datetime.date() in (today, tomorrow)
        ]

        summary_events = process_calendar_events(
            raw_events,
            truncate_to_tomorrow=True,
        )
        summary_events += summary_bin_events

        fullscreen_events = process_calendar_events(
            raw_events,
            truncate_to_tomorrow=False,
        )
        fullscreen_events += bin_events

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
