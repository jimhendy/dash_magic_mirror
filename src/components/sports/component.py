from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload
from utils.styles import COLORS

from .data import async_process_sports_data
from .full_screen import render_sports_fullscreen
from .summary import render_sports_summary


class Sports(DataDrivenComponent):
    """Upcoming fixtures for the configured teams (see `data.SPORTS`),
    scraped from Where's The Match.

    Tile: the next few fixtures this week. Panel: every fixture, grouped by
    day, filterable by sport.
    """

    title = "Sport"
    icon = "mdi:trophy-outline"
    accent = COLORS["orange"]
    jitter_seconds = 30
    placeholder_error = "Sports unavailable"
    placeholder_loading = "Loading fixtures…"

    def __init__(self, fetch_minutes: int = 360, **kwargs):
        self.refresh_seconds = max(int(fetch_minutes * 60), 60)
        super().__init__(name="sports", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        data = await async_process_sports_data()
        try:
            summary = render_sports_summary(data)
            detail = render_sports_fullscreen(data)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering sports payload")
            return None

        return ComponentPayload(
            summary=summary,
            detail=detail,
            subtitle="Upcoming fixtures and where to watch",
            raw=data,
        )
