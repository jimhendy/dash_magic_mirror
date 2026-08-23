"""Data + parsing helpers for the News component.

Sources headlines from one or more standard RSS 2.0 feeds. No API key is
required and feeds are parsed with the stdlib XML parser, so no extra
dependency is needed.
"""

from __future__ import annotations

import asyncio
import datetime
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any

import httpx
from loguru import logger

from utils.file_cache import cache_json

from .constants import FLUFF_KEYWORDS, FLUFF_LINK_PATTERNS, HTTP_TIMEOUT, ITEM_LIMIT


@cache_json(valid_lifetime=datetime.timedelta(minutes=20))
def fetch_news_rss(rss_url: str) -> str:
    """Fetch the raw RSS XML for a single news feed."""
    try:
        response = httpx.get(
            rss_url,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MagicMirror/1.0)"},
        )
        response.raise_for_status()
        return response.text
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to fetch news RSS from {rss_url}: {e}")
        return ""


async def async_fetch_news_rss(rss_url: str) -> str:
    """Async wrapper for fetching the raw RSS XML."""
    return await asyncio.to_thread(fetch_news_rss, rss_url)


def _is_fluff(title: str, link: str) -> bool:
    """A title alone rarely reveals a Sport/Entertainment story that leaked
    into a World feed (see `FLUFF_LINK_PATTERNS`), so this checks both.
    """
    lowered_title = title.lower()
    if any(keyword in lowered_title for keyword in FLUFF_KEYWORDS):
        return True
    lowered_link = link.lower()
    return any(pattern in lowered_link for pattern in FLUFF_LINK_PATTERNS)


def _parse_pub_date(pub_date: str) -> datetime.datetime:
    """Parse an RSS `pubDate` (RFC 822) for sorting; undated/unparsable
    items sort last rather than crashing the merge.
    """
    try:
        parsed = parsedate_to_datetime(pub_date)
    except (TypeError, ValueError):
        return datetime.datetime.min.replace(tzinfo=datetime.UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return parsed


def parse_news_items(raw_xml: str, limit: int = ITEM_LIMIT) -> list[dict[str, Any]]:
    """Parse a single RSS 2.0 feed into a flat list of headline dicts,
    dropping items that look like filler rather than news.
    """
    if not raw_xml.strip():
        return []

    try:
        root = ET.fromstring(raw_xml)  # noqa: S314 - trusted, fixed feed URLs, not user input
    except ET.ParseError as e:
        logger.error(f"Failed to parse news RSS: {e}")
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    source = (channel.findtext("title") or "News").strip()

    items: list[dict[str, Any]] = []
    for item in channel.findall("item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or _is_fluff(title, link):
            continue
        items.append(
            {
                "title": title,
                "source": source,
                "link": link,
                "pub_date": (item.findtext("pubDate") or "").strip(),
            },
        )
    return items


async def async_fetch_news_items(
    rss_urls: list[str],
    limit: int = ITEM_LIMIT,
) -> list[dict[str, Any]]:
    """Fetch and parse every configured RSS feed, merging them into one
    headline list sorted newest-first (interleaving sources rather than
    running through one feed at a time).
    """
    raw_feeds = await asyncio.gather(
        *(async_fetch_news_rss(url) for url in rss_urls),
    )
    items = [item for raw_xml in raw_feeds for item in parse_news_items(raw_xml, limit)]
    items.sort(key=lambda item: _parse_pub_date(item["pub_date"]), reverse=True)
    return items[:limit]
