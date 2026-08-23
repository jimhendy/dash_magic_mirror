"""Data + parsing helpers for the News component.

Sources headlines from a standard RSS 2.0 feed (default: BBC News). No API
key is required and the feed is parsed with the stdlib XML parser, so no
extra dependency is needed.
"""

from __future__ import annotations

import asyncio
import datetime
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from loguru import logger

from utils.file_cache import cache_json

from .constants import HTTP_TIMEOUT, ITEM_LIMIT


@cache_json(valid_lifetime=datetime.timedelta(minutes=20))
def fetch_news_rss(rss_url: str) -> str:
    """Fetch the raw RSS XML for the news feed."""
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


def parse_news_items(raw_xml: str, limit: int = ITEM_LIMIT) -> list[dict[str, Any]]:
    """Parse an RSS 2.0 feed into a flat list of headline dicts."""
    if not raw_xml.strip():
        return []

    try:
        root = ET.fromstring(raw_xml)  # noqa: S314 - trusted, fixed feed URL, not user input
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
        if not title:
            continue
        items.append(
            {
                "title": title,
                "source": source,
                "link": (item.findtext("link") or "").strip(),
                "pub_date": (item.findtext("pubDate") or "").strip(),
            },
        )
    return items


async def async_fetch_news_items(
    rss_url: str,
    limit: int = ITEM_LIMIT,
) -> list[dict[str, Any]]:
    """Fetch and parse the configured RSS feed into headline dicts."""
    raw_xml = await async_fetch_news_rss(rss_url)
    return parse_news_items(raw_xml, limit=limit)
