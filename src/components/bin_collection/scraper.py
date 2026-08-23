"""Headless-browser scrape of Waltham Forest Council's bin-collection lookup.

The council's "Find My Bin Collection Dates" tool (an AchieveForms/Firmstep
form) has no static or documented API: the postcode/address lookup and the
collection-date query it triggers both run through a `/apibroker/runLookup`
endpoint gated behind a session (`sid`) and CSRF token that only get minted
by the page's own JavaScript as it loads - there's no way to reach them with
plain HTTP requests. Driving a real headless browser through the same steps
a person would (enter postcode, pick the address, read the result) sidesteps
that entirely: it's slower and heavier than a raw API call, but it only runs
once every few days (see `CACHE_LIFETIME`) and keeps working even if the
council changes the underlying API, since it's just using the page as built.
"""

import datetime
import re
import time

from playwright.sync_api import sync_playwright

from utils.dates import local_today
from utils.file_cache import cache_json

from .constants import (
    FORM_URL,
    PAGE_LOAD_TIMEOUT_MS,
    RESULT_TIMEOUT_MS,
    CACHE_LIFETIME,
)

# Matches each result block the site renders into the `binCollectionHTML`
# field, e.g.:
#   <h5>Food Waste Collection Service</h5>
#   <img src="..." alt="..." />
#   <p>First collection: <br /><b>Tuesday 25 August<b></p>
_COLLECTION_RE = re.compile(
    r"<h5>([^<]+)</h5>.*?<b>([^<]+)<b>",
    re.DOTALL,
)


def _parse_uk_date(day_month: str, *, reference: datetime.date) -> datetime.date | None:
    """Parse "Tuesday 25 August" (no year) into a real date, assuming the
    nearest occurrence on or after `reference` - the site never says which
    year, and a next-collection date is always in the near future.
    """
    parts = day_month.split()
    if len(parts) != 3:
        return None
    _weekday, day_str, month_name = parts
    try:
        day = int(day_str)
        month = datetime.datetime.strptime(month_name, "%B").month
    except ValueError:
        return None

    for year in (reference.year, reference.year + 1):
        try:
            candidate = datetime.date(year, month, day)
        except ValueError:
            continue
        if candidate >= reference:
            return candidate
    return None


def _scrape(postcode: str, address_text: str) -> list[dict]:
    """Drive the real form and return raw {service_name, date_text} pairs.

    Kept separate from the cached/parsed entry point so failures are easy to
    reason about: this only deals in the site's own words, date parsing and
    category short-naming happen afterwards in `data.py`.
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(FORM_URL, timeout=PAGE_LOAD_TIMEOUT_MS, wait_until="networkidle")

            frame = page.frame_locator("#fillform-frame-1")

            # Field ids match the AchieveForms field `name` values directly
            # (confirmed against the real rendered form) - more stable than
            # matching on label text, and unambiguous: the address field's
            # accessible label also matches a select2 helper element, which
            # made `get_by_label` resolve to two elements.
            postcode_input = frame.locator("#postcode_search")
            postcode_input.wait_for(timeout=PAGE_LOAD_TIMEOUT_MS)
            postcode_input.fill(postcode)
            postcode_input.press("Tab")

            # select2 hides the real <select> behind its own widget, so it
            # never becomes CSS "visible" - wait for attachment instead, and
            # pass force=True to select_option (which otherwise refuses to
            # act on a non-visible element). Selecting the underlying
            # <select> directly still fires the native `change` event the
            # form's own JS listens on, same as if select2's UI had been
            # clicked. Wait separately for the actual address option to
            # exist first, since the option list populates async after the
            # postcode lookup responds.
            address_select = frame.locator("#YourAddress")
            address_select.wait_for(state="attached", timeout=RESULT_TIMEOUT_MS)
            address_option = frame.locator("#YourAddress option", has_text=address_text)
            address_option.first.wait_for(state="attached", timeout=RESULT_TIMEOUT_MS)
            try:
                address_select.select_option(label=address_text, force=True)
            except Exception:  # noqa: BLE001
                # Exact label match failed (e.g. slightly different
                # formatting) - fall back to whichever option contains it.
                option_value = address_option.first.get_attribute("value")
                if not option_value:
                    raise
                address_select.select_option(value=option_value, force=True)

            # Selecting the address triggers the site's own collection-dates
            # lookup; `siteCollectionsSuccessFlag` flips to "true" once it
            # resolves and `binCollectionHTML` gets populated. Both are
            # plain hidden form fields (not visible DOM text), so their live
            # `.value` is read directly rather than scraping rendered text.
            success_flag = frame.locator("#siteCollectionsSuccessFlag")
            success_flag.wait_for(state="attached", timeout=RESULT_TIMEOUT_MS)
            deadline = time.monotonic() + RESULT_TIMEOUT_MS / 1000
            while success_flag.input_value() != "true":
                if time.monotonic() > deadline:
                    msg = "Bin collection lookup did not complete in time"
                    raise TimeoutError(msg)
                page.wait_for_timeout(500)

            html_value = frame.locator("#binCollectionHTML").input_value()
        finally:
            browser.close()

    return [
        {"service_name": service_name.strip(), "date_text": date_text.strip()}
        for service_name, date_text in _COLLECTION_RE.findall(html_value)
    ]


@cache_json(valid_lifetime=CACHE_LIFETIME)
def fetch_bin_collections(postcode: str, address_text: str) -> list[dict]:
    """Scrape (or return the cached result of scraping) the council's bin
    collection tool.

    Deliberately lets scrape failures raise rather than catching them here:
    `cache_json` only writes a cache file for a *successful* return, so a
    transient failure just gets retried on the next refresh cycle instead of
    caching an empty result for the full 3-day lifetime - a much worse
    failure mode for something meant to remind you to put the bins out. The
    caller (`GoogleCalendar`) already catches and logs this, and simply
    shows no bin entries until the next successful scrape.
    """
    raw = _scrape(postcode, address_text)
    today = local_today()
    entries = []
    for row in raw:
        collection_date = _parse_uk_date(row["date_text"], reference=today)
        if collection_date is None:
            continue
        entries.append(
            {"service_name": row["service_name"], "date": collection_date.isoformat()},
        )
    return entries
