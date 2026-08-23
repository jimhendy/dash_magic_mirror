"""Markets component: S&P 500, FTSE 100, and ACWI levels.

Sourced from Yahoo Finance's public chart endpoint - no API key needed,
so there's nothing to rate-limit beyond the usual `cache_json` cadence.
"""

from dash import html
from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload

from .data import async_process_all_markets
from .full_screen import render_markets_fullscreen
from .summary import render_markets_summary


class Markets(DataDrivenComponent):
    refresh_seconds = 30 * 60
    jitter_seconds = 120
    placeholder_error = "Markets unavailable"
    placeholder_loading = "Loading markets..."

    def __init__(self, **kwargs):
        super().__init__(name="markets", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        markets = await async_process_all_markets()
        if not markets:
            return ComponentPayload(
                summary=self._build_placeholder(self.placeholder_error)
            )

        try:
            summary_children = render_markets_summary(markets)
            content = render_markets_fullscreen(markets)
        except Exception:  # noqa: BLE001
            logger.exception("Error rendering markets payload")
            return ComponentPayload(
                summary=self._build_placeholder(self.placeholder_error)
            )

        title = html.Div(
            "Markets",
            className="text-m",
            **{"data-component-name": self.name},
        )
        return ComponentPayload(
            summary=summary_children,
            fullscreen_title=title,
            fullscreen_content=content,
            raw={"markets": markets},
        )
