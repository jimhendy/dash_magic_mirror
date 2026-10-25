"""Markets component: S&P 500, FTSE 100, and ACWI levels.

Sourced from Yahoo Finance's public chart endpoint - no API key needed,
so there's nothing to rate-limit beyond the usual `cache_json` cadence.
"""

from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload
from utils.styles import COLORS

from .data import async_process_all_markets
from .full_screen import render_markets_fullscreen
from .summary import render_markets_summary


class Markets(DataDrivenComponent):
    title = "Markets"
    icon = "mdi:chart-line"
    accent = COLORS["accent"]
    refresh_seconds = 30 * 60
    jitter_seconds = 120
    placeholder_error = "Markets unavailable"
    placeholder_loading = "Loading markets…"

    def __init__(self, **kwargs):
        super().__init__(name="markets", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        markets = await async_process_all_markets()
        if not markets:
            return None

        try:
            summary = render_markets_summary(markets)
            detail = render_markets_fullscreen(markets)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering markets payload")
            return None

        return ComponentPayload(
            summary=summary,
            detail=detail,
            subtitle="Closing levels · 3 months",
            raw={"markets": markets},
        )
