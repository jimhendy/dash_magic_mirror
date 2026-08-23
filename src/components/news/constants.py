"""Constants for the News component."""

# World/hard-news sections specifically, not each outlet's general front-page
# feed - BBC's own general feed (the previous default) mixes in Sport and
# entertainment stories ("footballer's new haircut" territory) alongside
# actual news. Two outlets rather than one so a single source's editorial
# judgment (or an outage) doesn't define the whole headline list.
DEFAULT_RSS_URLS: list[str] = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theguardian.com/world/rss",
]
HTTP_TIMEOUT: int = 30
ITEM_LIMIT: int = 12
ROTATE_INTERVAL_MS: int = 8_000  # cadence for rotating the summary headline

# Title keywords that reliably signal filler rather than news, even from a
# "World" section (in-pictures round-ups, quizzes, etc.) - a coarse second
# line of defence behind picking serious sources in the first place.
FLUFF_KEYWORDS: tuple[str, ...] = (
    "in pictures",
    "in maps",
    "quiz:",
    "your pictures",
    "as it happened",
)

# A story's title alone rarely reveals it's actually Sport/Entertainment
# trivia (e.g. "'New season, new trim' - Haaland reveals buzzcut" gives no
# hint), but BBC's own article URL does - even a Sport story that leaks into
# the World feed still links to a /sport/... path. Checked against the
# item's link, not its title.
FLUFF_LINK_PATTERNS: tuple[str, ...] = (
    "/sport/",
    "/entertainment",
)

__all__ = [
    "DEFAULT_RSS_URLS",
    "FLUFF_KEYWORDS",
    "FLUFF_LINK_PATTERNS",
    "HTTP_TIMEOUT",
    "ITEM_LIMIT",
    "ROTATE_INTERVAL_MS",
]
