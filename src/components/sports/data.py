import asyncio
import datetime
import random
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from utils.dates import local_today, utc_now
from utils.file_cache import cache_json

from .constants import FETCH_RANGE_DAYS, HTTP_TIMEOUT, USER_AGENT, WTM_BASE_URL


@dataclass(frozen=True, kw_only=True)
class Sport:
    url: str  # URL fragment e.g. "rugby-union"
    teams: list[str]  # Team / club name substrings (lower-case matching)
    icon: str  # Iconify icon name e.g. "mdi:rugby"
    icon_color: str = "#FFFFFF"  # Icon color (optional)
    display_name: str = ""  # Friendly name (optional)
    team_icon_map: dict[str, str] | None = None  # optional per-team iconify icon codes


# Configure the sports / teams you care about
SPORTS: list[Sport] = [
    Sport(
        url="rugby-union",
        teams=["scotland", "ireland", "munster", "glasgow warriors"],
        display_name="Rugby",
        icon="mdi:rugby",
        icon_color="#4CAF50",  # Green for rugby
        team_icon_map={
            # NOTE: Using approximate / generic emblem icons available in Iconify. Replace with custom SVG if desired.
            "scotland": "mdi:flag-variant",  # Placeholder for Scotland Rugby
            "ireland": "mdi:clover",  # Shamrock style
            "munster": "mdi:crown",  # Placeholder emblem
            "glasgow warriors": "mdi:shield-sword",  # Warrior style
        },
    ),
    Sport(
        url="cricket",
        teams=["england"],
        display_name="Cricket",
        icon="mdi:cricket",
        icon_color="#FF9800",
        team_icon_map={
            "england": "mdi:shield-cross",  # St George style
        },
    ),  # Orange for cricket
    Sport(
        url="football",
        teams=["everton"],
        display_name="Football",
        icon="mdi:soccer",
        icon_color="#2196F3",  # Blue for football
        team_icon_map={
            "everton": "mdi:castle",  # Placeholder; swap with custom badge
        },
    ),
]

# Mapping from team name to crest ASSET PATH **per sport** to avoid cross-sport collisions
# Keys: sport.url -> { team_lower: asset_path }
SPORT_TEAM_CRESTS: dict[str, dict[str, str]] = {
    "rugby-union": {
        "munster": "/assets/crests/munster.svg",
        "glasgow warriors": "/assets/crests/glasgow.png",
        "scotland": "/assets/crests/scottish_rugby.ico",
        "ireland": "/assets/crests/ireland-rugby.jpg",
    },
    "cricket": {
        "england": "/assets/crests/england-cricket.svg",
        # intentionally NOT mapping 'ireland' to avoid showing rugby crest in cricket context
    },
    "football": {
        "everton": "/assets/crests/everton.ico",
    },
}


# -------- Pagination configuration (kept local to avoid changing constants module) --------
MAX_PAGES_PER_FETCH: int = 5  # safety cap
REQUEST_JITTER_MIN: float = 1.2
REQUEST_JITTER_MAX: float = 2.6
MAX_RETRIES_PER_PAGE: int = 1  # in addition to the initial attempt


def _date_str(d: datetime.date) -> str:
    return d.strftime("%Y%m%d")


@cache_json(valid_lifetime=datetime.timedelta(hours=36))
def fetch_raw_html_for_sport(sport: Sport) -> str:
    """Cache the raw HTML response for better development iteration."""
    start = local_today()
    end = start + datetime.timedelta(days=FETCH_RANGE_DAYS)
    url = (
        f"{WTM_BASE_URL}/live-{sport.url}-on-tv/"
        f"?showdatestart={_date_str(start)}&showdateend={_date_str(end)}"
    )
    logger.info(f"Fetching raw HTML for sport={sport.url} url={url}")
    try:
        resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return ""


# -------- Pagination helpers --------


def _pager_total_pages_from_html(html: str) -> int:
    """Parse total pages from the pager anchors. Returns at least 1.

    Looks for a table/div with id="gui-paging" and extracts the largest numeric link.
    Falls back to scanning all anchors for numeric text.
    """
    if not html:
        return 1
    try:
        soup = BeautifulSoup(html, "html.parser")
        container = soup.find(id="gui-paging")
        anchors = []
        if container:
            anchors = container.find_all("a")
        if not anchors:
            anchors = soup.find_all("a")
        nums: list[int] = []
        for a in anchors:
            t = (a.get_text() or "").strip()
            if t.isdigit():
                try:
                    nums.append(int(t))
                except ValueError:
                    pass
        if nums:
            return max(nums)
    except Exception as e:
        logger.debug(f"Failed parsing pager: {e}")
    return 1


def _extract_match_id_from_row(row: Any) -> str | None:
    """Try to extract a stable numeric match id from the row's buy/watch link.

    Expected formats include:
      - /match/some-slug/187664/
      - https://www.wheresthematch.com/match/some-slug/187664/
    """
    try:
        a = row.find("a", class_=re.compile(r"\bmobile-buy-pass\b"))
        href = a.get("href") if a else None
        if not href:
            return None
        # Remove any surrounding quotes artefacts and domain prefix
        href = href.replace("&quot;", "").replace('"', "").strip()
        # Look for the numeric id
        m = re.search(r"/match/[^/]+/(\d+)/", href)
        if not m:
            m = re.search(r"/(\d+)/?", href)
        return m.group(1) if m else None
    except Exception:
        return None


def _date_time_from_iso(date_str: str) -> tuple[datetime.date | None, str]:
    """Parse date/time from ISO 8601 strings like '2025-09-14T14:30:00Z'."""
    if not date_str.strip():
        return None, ""

    try:
        dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.date(), dt.strftime("%H:%M")
    except ValueError:
        return None, ""


def _extract_teams(fixture_line: str) -> tuple[str, str]:
    """Extract home and away teams from fixture line."""
    # Split on ' v ' (with spaces) first, then try ' vs '
    if " v " in fixture_line:
        parts = fixture_line.split(" v ", 1)
    elif " vs " in fixture_line:
        parts = fixture_line.split(" vs ", 1)
    else:
        return "", ""

    if len(parts) == 2:
        home = parts[0].strip()
        # Remove competition name from away team (everything after double space)
        away_full = parts[1].strip()
        away = re.split(r"\s{2,}", away_full)[
            0
        ].strip()  # Take first part before double spaces
        return home, away

    return "", ""


def _is_team_match(home: str, away: str, team_subs: list[str]) -> bool:
    """Check if home or away team matches any of the configured teams."""
    home_lower = home.lower().strip()
    away_lower = away.lower().strip()

    for team in team_subs:
        if home_lower == team or away_lower == team:
            return True
    return False


def _extract_competition(fixture_text: str) -> str:
    """Extract competition name from fixture text, filtering out login prompts."""
    parts = re.split(r"\s{2,}", fixture_text)
    if len(parts) > 1:
        competition = parts[-1].strip()
        # Filter out website login prompts
        if competition.lower() in [
            "log in to view",
            "login to view",
            "sign in to view",
        ]:
            return ""
        return competition.removesuffix(" Hide non-televised fixtures")
    return ""


def _tidy_channel_name(name: str) -> str:
    """Tidy up channel names by removing common suffixes."""
    name = name.strip()
    for prefix, formatted_name in [
        ("sky sports", "Sky Sports"),
        ("sky", "Sky"),
        ("bt sport", "BT Sport"),
        ("bt", "BT"),
    ]:
        if name.lower().startswith(prefix):
            return formatted_name + name.lower().removeprefix(prefix).strip().title()
    return name


def _create_fixture_dict(
    sport: Sport,
    home: str,
    away: str,
    parsed_date: datetime.date | None,
    time_str: str,
    competition: str,
    channel: str,
    raw_text: str,
    date_time_raw: str = "",
    match_id: str | None = None,
) -> dict[str, Any]:
    """Create a standardized fixture dictionary."""
    # Determine if a specific team icon can override the generic sport icon
    team_icon = sport.icon
    if sport.team_icon_map:
        home_lower = home.lower().strip()
        away_lower = away.lower().strip()
        for key, value in sport.team_icon_map.items():
            if home_lower == key or away_lower == key:
                team_icon = value
                break
    # Sport-scoped crest lookup only
    crest_path = None
    crest_map = SPORT_TEAM_CRESTS.get(sport.url, {})
    for team_name in (home.lower(), away.lower()):
        if team_name in crest_map:
            crest_path = crest_map[team_name]
            break
    channel = _tidy_channel_name(channel)
    return {
        "sport_icon": team_icon,
        "sport_icon_color": sport.icon_color,
        "sport_name": sport.display_name or sport.url.title(),
        "raw": raw_text,
        "home": home,
        "away": away,
        "time": time_str,
        "competition": competition,
        "channel": channel,
        "parsed_date": parsed_date.isoformat() if parsed_date else None,
        "sort_date": parsed_date or datetime.date.max,
        "date_time_raw": date_time_raw,
        "fetched_at": utc_now().isoformat(),
        "crest": crest_path,
        "match_id": match_id,
    }


def extract_fixtures_from_html(html: str, sport: Sport) -> list[dict[str, Any]]:
    """Extract fixture data from the cached HTML."""
    if not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    fixtures = []
    team_subs = [t.lower() for t in sport.teams]

    # Try to find fixtures in table structure first
    rows = soup.find_all("tr")
    for row in rows:
        fixture_text = row.get_text(separator=" ").strip()

        if not fixture_text or not (" v " in fixture_text or " vs " in fixture_text):
            continue

        home, away = _extract_teams(fixture_text)
        if not home or not away:
            continue

        if not _is_team_match(home, away, team_subs):
            continue

        # Extract channel from channel-details cell
        channel_info = ""
        channel_cell = row.find("td", class_="channel-details")
        if channel_cell:
            img_tag = channel_cell.find("img")
            if img_tag and img_tag.get("title"):
                channel_info = img_tag.get("title")
            elif img_tag and img_tag.get("alt"):
                channel_info = img_tag.get("alt").replace(" logo", "")

        # Extract the date/time
        date_time_cell = row.find("td", class_="start-details")
        date_time_raw = ""
        if date_time_cell and date_time_cell.get("content"):
            date_time_raw = date_time_cell.get("content").strip()
            parsed_date, time_str = _date_time_from_iso(date_time_raw)
        else:
            parsed_date, time_str = None, ""

        competition = _extract_competition(fixture_text)

        # Extract match id for dedupe
        match_id = _extract_match_id_from_row(row)

        fixtures.append(
            _create_fixture_dict(
                sport,
                home,
                away,
                parsed_date,
                time_str,
                competition,
                channel_info,
                fixture_text,
                date_time_raw=date_time_raw,
                match_id=match_id,
            ),
        )

    # Sort by date
    fixtures.sort(key=lambda x: x["sort_date"])
    logger.info(f"Extracted {len(fixtures)} fixtures for sport={sport.url}")
    return fixtures


# -------- Multi-page fetching --------


@cache_json(valid_lifetime=datetime.timedelta(hours=36))
def fetch_paginated_html_for_sport(sport: Sport) -> list[str]:
    """Fetch and cache all HTML pages for a sport within the date range.

    Strategy:
      - GET page 0 with date range
      - Parse total pages from pager
      - POST remaining pages with form fields (page, repost, showdatestart, showdateend)
    """
    start = local_today()
    end = start + datetime.timedelta(days=FETCH_RANGE_DAYS)
    start_s = _date_str(start)
    end_s = _date_str(end)

    first_url = (
        f"{WTM_BASE_URL}/live-{sport.url}-on-tv/"
        f"?showdatestart={start_s}&showdateend={end_s}"
    )
    post_url = f"{WTM_BASE_URL}/live-{sport.url}-on-tv/?paging=true"

    pages_html: list[str] = []

    headers_base = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }

    with httpx.Client(timeout=HTTP_TIMEOUT, headers=headers_base) as client:
        # First page (GET)
        logger.info(f"Fetching page 0 for sport={sport.url} url={first_url}")
        try:
            r0 = client.get(first_url)
            r0.raise_for_status()
            html0 = r0.text
        except Exception as e:
            logger.error(f"Failed to fetch first page for {sport.url}: {e}")
            html0 = ""
        pages_html.append(html0)

        total_pages = _pager_total_pages_from_html(html0)
        if total_pages <= 1:
            return pages_html

        # Remaining pages via POST
        for page_index in range(1, min(total_pages, MAX_PAGES_PER_FETCH)):
            form = {
                "page": str(page_index),
                "repost": "True",
                "showdatestart": start_s,
                "showdateend": end_s,
            }
            headers = {
                **headers_base,
                "Origin": WTM_BASE_URL,
                "Referer": first_url,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            attempt = 0
            html_i = ""
            while attempt <= MAX_RETRIES_PER_PAGE:
                try:
                    logger.info(
                        f"Fetching page {page_index} for sport={sport.url} via POST {post_url}",
                    )
                    resp = client.post(post_url, data=form, headers=headers)
                    resp.raise_for_status()
                    html_i = resp.text
                    break
                except Exception as e:
                    attempt += 1
                    if attempt > MAX_RETRIES_PER_PAGE:
                        logger.error(
                            f"Failed to fetch page {page_index} for {sport.url}: {e}",
                        )
                        html_i = ""
                        break
                    # small backoff before retry
                    time.sleep(random.uniform(REQUEST_JITTER_MIN, REQUEST_JITTER_MAX))

            pages_html.append(html_i)

            # polite pacing
            time.sleep(random.uniform(REQUEST_JITTER_MIN, REQUEST_JITTER_MAX))

    return pages_html


def fetch_fixtures_for_sport(sport: Sport) -> list[dict[str, Any]]:
    """Fetch and extract fixtures for a sport across all paginated pages.

    Aggregates fixtures from all pages, de-duplication by match id (if available)
    falling back to a composite key.
    """
    pages = fetch_paginated_html_for_sport(sport)

    seen_keys: set[str] = set()
    results: list[dict[str, Any]] = []

    for page_html in pages:
        fixtures = extract_fixtures_from_html(page_html, sport)
        for fx in fixtures:
            # Build dedupe key
            if fx.get("match_id"):
                key = f"id:{fx['match_id']}"
            else:
                key = ":".join(
                    [
                        fx.get("date_time_raw")
                        or f"{fx.get('parsed_date')} {fx.get('time')}",
                        fx.get("home", "").lower(),
                        fx.get("away", "").lower(),
                        fx.get("competition", "").lower(),
                    ],
                )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            results.append(fx)

    # Sort by date
    results.sort(key=lambda x: x.get("sort_date", datetime.date.max))
    logger.info(
        f"Total fixtures aggregated for sport={sport.url}: {len(results)} across {len(pages)} page(s)",
    )
    return results


def fetch_all_fixtures() -> dict[str, Any]:
    """Fetch all fixtures for all configured sports."""
    aggregate: dict[str, Any] = {
        "updated": utc_now().isoformat(),
        "sports": {},
    }
    for sport in SPORTS:
        aggregate["sports"][sport.url] = fetch_fixtures_for_sport(sport)
    return aggregate


def process_sports_data() -> dict[str, Any]:
    """Process and return sports fixture data."""
    return fetch_all_fixtures()


async def async_process_sports_data() -> dict[str, Any]:
    """Async wrapper to fetch sports data without blocking the event loop."""
    return await asyncio.to_thread(process_sports_data)


def get_summary_fixtures(
    data: dict[str, Any],
    limit: int = 3,
    days_ahead: int = 7,
) -> list[dict[str, Any]]:
    """Get fixtures for summary view - limited to next 7 days and max 3 items."""
    if not data or "sports" not in data:
        return []

    all_fixtures: list[dict[str, Any]] = []
    for sport_key, items in data["sports"].items():
        if isinstance(items, list):
            all_fixtures.extend(items)

    # Filter to next 7 days only
    today = local_today()
    cutoff_date = today + datetime.timedelta(days=days_ahead)

    filtered_fixtures = []
    for fx in all_fixtures:
        if fx.get("parsed_date"):
            try:
                fixture_date = datetime.date.fromisoformat(fx["parsed_date"])
                if today <= fixture_date <= cutoff_date:
                    filtered_fixtures.append(fx)
            except ValueError:
                continue

    # Sort by date and limit
    filtered_fixtures.sort(key=lambda x: x.get("sort_date", datetime.date.max))
    return filtered_fixtures[:limit]


def get_full_screen_fixtures(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Get all fixtures for full screen view."""
    if not data or "sports" not in data:
        return []

    all_fixtures: list[dict[str, Any]] = []
    for sport_key, items in data["sports"].items():
        if isinstance(items, list):
            all_fixtures.extend(items)

    # Sort by date
    all_fixtures.sort(key=lambda x: x.get("sort_date", datetime.date.max))
    return all_fixtures
