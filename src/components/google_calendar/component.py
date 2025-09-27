"""Google Calendar component for the Magic Mirror application.

Displays today and tomorrow's events in a calendar-like layout.
Uses Google Calendar API for event data.
"""

from dash import Input, Output, dcc, html, no_update
from loguru import logger

from components.base import BaseComponent, PreloadedFullScreenMixin
from utils.data_repository import ComponentPayload, get_repository

from .data import async_fetch_calendar_events, process_calendar_events


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
        self._repository = get_repository()
        self._data_key = self.name
        self._refresh_seconds = 5 * 60  # matches interval below
        try:
            self._repository.register_component(
                self._data_key,
                refresh_coro=self._build_payload,
                interval_seconds=self._refresh_seconds,
                jitter_seconds=30,
            )
            self._initial_payload = self._repository.refresh_now_sync(self._data_key)
        except ValueError:
            self._initial_payload = self._repository.get_payload_snapshot(
                self._data_key,
            )

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
                summary=self._build_placeholder("Calendar unavailable"),
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

    def _build_placeholder(self, message: str) -> html.Div:
        return html.Div(
            message,
            style={
                "color": "#FF6B6B",
                "textAlign": "center",
                "padding": "1rem",
                "fontSize": "1.1rem",
            },
        )

    def _latest_payload(self) -> ComponentPayload | None:
        return (
            self._repository.get_payload_snapshot(self._data_key)
            or self._initial_payload
        )

    def _summary_layout(self):
        """Returns the layout of the Google Calendar component."""
        payload = self._latest_payload()
        summary_children = (
            payload.summary
            if payload and payload.summary is not None
            else self._build_placeholder("Loading calendar...")
        )
        stores = self.preload_fullscreen_stores(
            title=payload.fullscreen_title if payload else None,
            content=payload.fullscreen_content if payload else None,
        )
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=self._refresh_seconds * 1000,
                    n_intervals=0,
                ),
                *stores,
                html.Div(
                    id=f"{self.component_id}-content",
                    children=summary_children,
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
        repo = self._repository
        data_key = self._data_key

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval", "n_intervals"),
            prevent_initial_call=False,
        )
        async def hydrate_calendar(_n):
            payload = await repo.get_payload_async(data_key)
            if payload is not None:
                self._initial_payload = payload
            else:
                payload = self._latest_payload()

            if payload is None:
                placeholder = self._build_placeholder("Calendar unavailable")
                return placeholder, no_update, no_update

            return (
                payload.summary,
                payload.fullscreen_title,
                payload.fullscreen_content,
            )
