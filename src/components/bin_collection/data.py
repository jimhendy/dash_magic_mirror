"""Turn a bin-collection scrape into calendar-shaped entries.

Kept separate from the scrape itself (`scraper.py`): this only deals with
already-parsed {service_name, date} rows, merging same-date collections into
a single entry with short category names, per-day, the way they should
actually appear on the calendar.
"""

import asyncio
import datetime

from components.google_calendar.data import CalendarEvent
from utils.dates import get_app_timezone

from .constants import short_category_name
from .scraper import fetch_bin_collections


async def async_fetch_bin_collections(postcode: str, address_text: str) -> list[dict]:
    """Async wrapper around the cached, synchronous scrape."""
    return await asyncio.to_thread(fetch_bin_collections, postcode, address_text)


def build_bin_collection_events(entries: list[dict]) -> list[CalendarEvent]:
    """Merge same-date bin collections into one all-day `CalendarEvent` each,
    titled with the short category names (e.g. "Food, Recycling").
    """
    by_date: dict[str, list[str]] = {}
    for entry in entries:
        category = short_category_name(entry["service_name"])
        by_date.setdefault(entry["date"], []).append(category)

    events = []
    for date_str, categories in by_date.items():
        # Stable, readable order regardless of scrape order.
        ordered = [
            c for c in ("Food", "Recycling", "Refuse", "Garden") if c in categories
        ]
        start = datetime.datetime.fromisoformat(date_str + "T00:00:00").replace(
            tzinfo=get_app_timezone(),
        )
        events.append(
            CalendarEvent(
                id=f"bin-collection-{date_str}",
                title=", ".join(ordered),
                start_datetime=start,
                end_datetime=start,
                is_all_day=True,
                is_multi_day=False,
                starts_before_today=False,
                ends_after_tomorrow=False,
                calendar_id="bin_collection",
            ),
        )
    return events
