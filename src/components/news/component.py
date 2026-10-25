"""News headlines component for the Magic Mirror application.

Sourced from one or more RSS feeds (default: BBC World + Guardian World) - no
API key required, so there is nothing to rate-limit beyond the usual
`cache_json` fetch cadence.
"""

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload

from .constants import DEFAULT_RSS_URLS, ITEM_LIMIT
from .data import async_fetch_news_items
from .full_screen import render_news_fullscreen
from .summary import render_news_summary


class News(DataDrivenComponent):
    """Rotating news headlines, sourced from one or more RSS feeds."""

    title = "Headlines"
    icon = "mdi:newspaper-variant-outline"
    refresh_seconds = 20 * 60
    jitter_seconds = 60
    placeholder_error = "News unavailable"
    placeholder_loading = "Loading news…"

    def __init__(
        self,
        rss_urls: list[str] = DEFAULT_RSS_URLS,
        item_limit: int = ITEM_LIMIT,
        **kwargs,
    ):
        self.rss_urls = rss_urls
        self.item_limit = item_limit
        super().__init__(name="news", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        items = await async_fetch_news_items(self.rss_urls, limit=self.item_limit)
        return ComponentPayload(
            summary=render_news_summary(items),
            detail=render_news_fullscreen(items),
            subtitle=" · ".join(
                sorted({i.get("source", "") for i in items if i.get("source")})
            ),
            raw={"items": items},
        )
