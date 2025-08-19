import datetime
import re
from dataclasses import dataclass
from typing import Any

import httpx
from bs4 import BeautifulSoup
from dash import Input, Output, dcc, html
from dash_iconify import DashIconify
from loguru import logger

from components.base import BaseComponent
from utils.file_cache import cache_json
from utils.styles import COLORS


@dataclass(frozen=True, kw_only=True)
class Sport:
    url: str  # URL fragment e.g. "rugby-union"
    teams: list[str]  # Team / club name substrings (lower-case matching)
    icon: str  # Iconify icon name e.g. "mdi:rugby"
    icon_color: str = "#FFFFFF"  # Icon color (optional)
    display_name: str = ""  # Friendly name (optional)


# Configure the sports / teams you care about
SPORTS: list[Sport] = [
    Sport(
        url="rugby-union",
        teams=["scotland", "ireland", "munster", "glasgow"],
        display_name="Rugby",
        icon="mdi:rugby",
        icon_color="#4CAF50",  # Green for rugby
    ),
    Sport(
        url="cricket",
        teams=["england"],
        display_name="Cricket",
        icon="mdi:cricket",
        icon_color="#FF9800",
    ),  # Orange for cricket
    Sport(
        url="football",
        teams=["everton"],
        display_name="Football",
        icon="mdi:soccer",
        icon_color="#2196F3",  # Blue for football
    ),
]

FETCH_RANGE_DAYS = 31
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


def _date_str(d: datetime.date) -> str:
    return d.strftime("%Y%m%d")


@cache_json(valid_lifetime=datetime.timedelta(hours=6))
def fetch_raw_html_for_sport(sport: Sport) -> str:
    """Cache the raw HTML response for better development iteration."""
    start = datetime.date.today()
    end = start + datetime.timedelta(days=FETCH_RANGE_DAYS)
    url = (
        f"https://www.wheresthematch.com/live-{sport.url}-on-tv/"
        f"?showdatestart={_date_str(start)}&showdateend={_date_str(end)}"
    )
    logger.info(f"Fetching raw HTML for sport={sport.url} url={url}")
    try:
        resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return ""


def _parse_date_time(date_str: str) -> tuple[datetime.date | None, str]:
    """Parse date/time from strings like 'Fri 15th August 2025 08:10'."""
    if not date_str.strip():
        return None, ""

    # Extract time (HH:MM pattern)
    time_match = re.search(r"\b(\d{1,2}:\d{2})\b", date_str)
    time_str = time_match.group(1) if time_match else ""

    # Parse date - look for day, month, year patterns
    date_match = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})\b",
        date_str.lower(),
    )

    if date_match:
        day = int(date_match.group(1))
        month_name = date_match.group(2)
        year = int(date_match.group(3))

        month_map = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }

        month = month_map.get(month_name)
        if month:
            try:
                return datetime.date(year, month, day), time_str
            except ValueError:
                pass

    return None, time_str


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
) -> dict[str, Any]:
    """Create a standardized fixture dictionary."""
    return {
        "sport_icon": sport.icon,
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
        "fetched_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }


def extract_fixtures_from_html(html: str, sport: Sport) -> list[dict[str, Any]]:
    """Extract fixture data from the cached HTML."""
    if not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    fixtures = []
    team_subs = [t.lower() for t in sport.teams]

    # Try to find fixtures in table structure first
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            fixture_text = row.get_text(separator=" ").strip()

            if not fixture_text or not (
                " v " in fixture_text or " vs " in fixture_text
            ):
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

            # Extract date/time from the row
            parsed_date, time_str = None, ""
            for cell in cells:
                cell_text = cell.get_text().strip()
                if cell_text:
                    temp_date, temp_time = _parse_date_time(cell_text)
                    if temp_date or temp_time:
                        parsed_date, time_str = temp_date, temp_time
                        break

            competition = _extract_competition(fixture_text)

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
                ),
            )

    # If no table fixtures found, fall back to text parsing
    if not fixtures:
        text_lines = soup.get_text().split("\n")
        for i, line in enumerate(text_lines):
            line = line.strip()
            if not line or not (" v " in line or " vs " in line):
                continue

            home, away = _extract_teams(line)
            if not home or not away:
                continue

            if not _is_team_match(home, away, team_subs):
                continue

            # Get the next few lines for date/time info
            date_time_line = ""
            if i + 1 < len(text_lines):
                date_time_line = text_lines[i + 1].strip()

            parsed_date, time_str = _parse_date_time(date_time_line)
            competition = _extract_competition(line)

            fixtures.append(
                _create_fixture_dict(
                    sport,
                    home,
                    away,
                    parsed_date,
                    time_str,
                    competition,
                    "",
                    line,
                    date_time_line,
                ),
            )

    # Sort by date
    fixtures.sort(key=lambda x: x["sort_date"])
    logger.info(f"Extracted {len(fixtures)} fixtures for sport={sport.url}")
    return fixtures


def fetch_fixtures_for_sport(sport: Sport) -> list[dict[str, Any]]:
    """Fetch and extract fixtures for a sport."""
    html = fetch_raw_html_for_sport(sport)
    return extract_fixtures_from_html(html, sport)


def fetch_all_fixtures() -> dict[str, Any]:
    aggregate: dict[str, Any] = {
        "updated": datetime.datetime.utcnow().isoformat(),
        "sports": {},
    }
    for sport in SPORTS:
        aggregate["sports"][sport.url] = fetch_fixtures_for_sport(sport)
    return aggregate


class Sports(BaseComponent):
    def __init__(self, *args, fetch_minutes: int = 360, **kwargs):
        super().__init__(name="sports", *args, **kwargs)
        self.fetch_minutes = fetch_minutes

    def layout(self):
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval-fetch",
                    interval=self.fetch_minutes * 60_000,
                    n_intervals=0,
                ),
                dcc.Store(id=f"{self.component_id}-store", data=None),
                html.Div(
                    id=f"{self.component_id}-fixture",
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "stretch",
                        "gap": "8px",
                        "width": "100%",
                        "color": COLORS["pure_white"],
                    },
                ),
            ],
        )

    def add_callbacks(self, app):
        @app.callback(
            Output(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
            prevent_initial_call=False,
        )
        def _update_store(_n):
            try:
                return fetch_all_fixtures()
            except Exception as e:
                logger.error(f"Error fetching sports fixtures: {e}")
                return {}

        @app.callback(
            Output(f"{self.component_id}-fixture", "children"),
            Input(f"{self.component_id}-store", "data"),
            prevent_initial_call=False,
        )
        def _render_list(data):
            if not data or "sports" not in data:
                return html.Div(
                    "No upcoming fixtures",
                    style={
                        "color": COLORS["soft_gray"],
                        "textAlign": "center",
                        "padding": "2rem",
                    },
                )

            all_fixtures: list[dict[str, Any]] = []
            for sport_key, items in data["sports"].items():
                if isinstance(items, list):
                    all_fixtures.extend(items)

            # Sort by date, then limit
            all_fixtures.sort(key=lambda x: x.get("sort_date", datetime.date.max))

            if not all_fixtures:
                return html.Div(
                    "No upcoming fixtures",
                    style={
                        "color": COLORS["soft_gray"],
                        "textAlign": "center",
                        "padding": "2rem",
                    },
                )
            fixture_cards = []
            today = datetime.date.today()

            for fx in all_fixtures:
                # Format date nicely and check if it's today
                date_display = ""
                is_today = False
                date_obj = None
                if fx.get("parsed_date"):
                    try:
                        date_obj = datetime.date.fromisoformat(fx["parsed_date"])
                        is_today = date_obj == today
                        if is_today:
                            date_display = "TODAY"
                        else:
                            date_display = date_obj.strftime("%a %d %b")
                    except:  # noqa: E722
                        date_display = fx.get("date_time_raw", "")[:20]

                # Create fixture card with single-line layout
                fixture_card = html.Div(
                    [
                        html.Div(
                            [
                                # Left side: sport icon, teams, and competition
                                html.Div(
                                    [
                                        DashIconify(
                                            icon=fx.get(
                                                "sport_icon",
                                                "mdi:help-circle",
                                            ),
                                            style={
                                                "marginRight": "10px",
                                                "color": fx.get(
                                                    "sport_icon_color",
                                                    COLORS["primary_blue"],
                                                ),
                                                "flexShrink": "0",
                                            },
                                        ),
                                        html.Span(
                                            f"{fx.get('home', '?')} vs {fx.get('away', '?')}",
                                            style={
                                                "fontWeight": "bold"
                                                if is_today
                                                else "500",
                                                "color": COLORS["pure_white"],
                                                "marginRight": "5px",
                                                "flex": "1",
                                            },
                                        ),
                                        *(
                                            [
                                                html.Span(
                                                    fx.get("channel", ""),
                                                    className="text-vs",
                                                    style={
                                                        "color": COLORS[
                                                            "success_green"
                                                        ],
                                                        "marginRight": "5px",
                                                    },
                                                ),
                                            ]
                                            if fx.get("channel")
                                            else []
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "overflow": "hidden",
                                        "flex": "1",
                                    },
                                ),
                                # Right side: date and time
                                html.Div(
                                    [
                                        html.Span(
                                            date_display,
                                            style={
                                                "color": COLORS["accent_gold"]
                                                if is_today
                                                else COLORS["soft_gray"],
                                                "fontWeight": "bold"
                                                if is_today
                                                else "400",
                                                "marginRight": "8px",
                                            },
                                        ),
                                        html.Span(
                                            fx.get("time", ""),
                                            style={
                                                "color": COLORS["warm_orange"],
                                                "fontWeight": "500",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "whiteSpace": "nowrap",
                                        "textAlign": "right",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "space-between",
                                "width": "100%",
                                "gap": "8px",
                            },
                        ),
                    ],
                    className="text-s centered-content",
                    style={
                        "border": f"1px solid {COLORS['accent_gold']}"
                        if is_today
                        else "1px solid rgba(255,255,255,0.08)",
                        "borderRadius": "8px",
                        "padding": "2px 4px",
                        "marginBottom": "0",
                        "backdropFilter": "blur(10px)",
                        "opacity": self._opacity_from_days_away(date_obj),
                    },
                )

                fixture_cards.append(fixture_card)

            return fixture_cards
