"""Constants for the News component."""

DEFAULT_RSS_URL: str = "https://feeds.bbci.co.uk/news/rss.xml"
HTTP_TIMEOUT: int = 30
ITEM_LIMIT: int = 12
ROTATE_INTERVAL_MS: int = 8_000  # cadence for rotating the summary headline

__all__ = ["DEFAULT_RSS_URL", "HTTP_TIMEOUT", "ITEM_LIMIT", "ROTATE_INTERVAL_MS"]
