"""Data fetching for the Markets component.

Sourced from Yahoo Finance's public chart endpoint - undocumented but
widely relied on (the same endpoint `yfinance` and similar tools wrap), no
API key required. In the same spirit as the sports component's HTML
scrape: no official API is used, so this is inherently a little fragile
against upstream changes, but it costs nothing and needs no credentials.
"""

from __future__ import annotations

import asyncio
import datetime
from typing import Any

import httpx
from loguru import logger

from utils.file_cache import cache_json

from .constants import (
    BASE_URL,
    CHART_INTERVAL,
    CHART_RANGE,
    HTTP_TIMEOUT,
    MARKET_INDICES,
    USER_AGENT,
    MarketIndex,
)


@cache_json(valid_lifetime=datetime.timedelta(minutes=30))
def fetch_market_chart(symbol: str) -> dict[str, Any]:
    """Fetch OHLC chart data + summary stats for one symbol."""
    try:
        response = httpx.get(
            f"{BASE_URL}/{symbol}",
            params={"range": CHART_RANGE, "interval": CHART_INTERVAL},
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to fetch market chart for {symbol}: {e}")
        return {}


async def async_fetch_market_chart(symbol: str) -> dict[str, Any]:
    return await asyncio.to_thread(fetch_market_chart, symbol)


def process_market_data(
    raw: dict[str, Any], index: MarketIndex
) -> dict[str, Any] | None:
    """Extract a clean price series + summary stats from the raw chart response."""
    try:
        result = raw["chart"]["result"][0]
    except (KeyError, IndexError, TypeError):
        return None

    meta = result.get("meta", {})
    timestamps = result.get("timestamp") or []
    try:
        closes = result["indicators"]["quote"][0].get("close") or []
    except (KeyError, IndexError):
        closes = []

    series = [
        {"time": datetime.datetime.fromtimestamp(ts, tz=datetime.UTC), "close": close}
        for ts, close in zip(timestamps, closes, strict=False)
        if close is not None
    ]
    if not series:
        return None

    price = meta.get("regularMarketPrice", series[-1]["close"])
    previous_close = meta.get("chartPreviousClose") or series[-1]["close"]
    day_change_pct = (
        ((price - previous_close) / previous_close * 100) if previous_close else 0.0
    )

    return {
        "symbol": index.symbol,
        "label": index.label,
        "currency": meta.get("currency", ""),
        "price": price,
        "day_change_pct": day_change_pct,
        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
        "day_high": meta.get("regularMarketDayHigh"),
        "day_low": meta.get("regularMarketDayLow"),
        "volume": meta.get("regularMarketVolume"),
        "series": series,  # full CHART_RANGE, for the full-screen chart
    }


async def async_process_all_markets() -> list[dict[str, Any]]:
    """Fetch + process every configured index. Missing/failed ones are
    silently dropped rather than breaking the whole component.
    """
    results = []
    for index in MARKET_INDICES:
        raw = await async_fetch_market_chart(index.symbol)
        processed = process_market_data(raw, index)
        if processed:
            results.append(processed)
    return results


def summary_series(market: dict[str, Any], days: int) -> list[dict[str, Any]]:
    """The most recent `days` of a market's series - for the summary sparkline."""
    series = market.get("series") or []
    if not series:
        return []
    cutoff = series[-1]["time"] - datetime.timedelta(days=days)
    return [pt for pt in series if pt["time"] >= cutoff]


def change_pct(series: list[dict[str, Any]]) -> float:
    """% change from the first to the last point of a series."""
    if len(series) < 2:
        return 0.0
    first, last = series[0]["close"], series[-1]["close"]
    return ((last - first) / first * 100) if first else 0.0
