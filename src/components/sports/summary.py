import datetime
from typing import Any

from dash import html

from utils.dates import local_today
from utils.ui import badge, empty_state, icon

TILE_FIXTURES = 8
WINDOW_DAYS = 7


def fixture_date(fx: dict[str, Any]) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(fx.get("parsed_date") or "")
    except ValueError:
        return None


def when_label(date: datetime.date | None, time_str: str) -> str:
    today = local_today()
    if date is None:
        return time_str
    if date == today:
        day = "Today"
    elif date == today + datetime.timedelta(days=1):
        day = "Tomorrow"
    elif (date - today).days < 7:
        day = date.strftime("%a")
    else:
        day = f"{date:%a} {date.day} {date:%b}"
    return f"{day} {time_str}".strip()


def crest(fx: dict[str, Any]) -> html.Div:
    """The followed team's crest where known, else the sport's icon."""
    if fx.get("crest"):
        return html.Div(html.Img(src=fx["crest"], alt=""), className="crest")
    return html.Div(
        icon(fx.get("sport_icon", "mdi:trophy-outline"), "crest__icon"),
        className="crest crest--icon",
        style={"--crest": fx.get("sport_icon_color", "#888")},
    )


def render_sports_summary(data: dict[str, Any]) -> html.Div:
    from .data import get_summary_fixtures

    fixtures = get_summary_fixtures(data, limit=TILE_FIXTURES, days_ahead=WINDOW_DAYS)
    if not fixtures:
        return empty_state("No fixtures this week", "mdi:trophy-outline")

    today = local_today()
    rows = []
    for fx in fixtures:
        date = fixture_date(fx)
        rows.append(
            html.Div(
                [
                    crest(fx),
                    html.Div(
                        [
                            html.Div(
                                f"{fx.get('home', '')} v {fx.get('away', '')}",
                                className="fx__teams truncate",
                            ),
                            html.Div(
                                fx.get("competition") or fx.get("sport_name", ""),
                                className="fx__comp truncate",
                            ),
                        ],
                        className="fx__text",
                    ),
                    html.Div(
                        [
                            html.Div(
                                when_label(date, fx.get("time", "")),
                                className="fx__when",
                            ),
                            html.Div(
                                fx.get("channel", ""), className="fx__channel truncate"
                            ),
                        ],
                        className="fx__right",
                    ),
                ],
                className="fx" + (" is-today" if date == today else ""),
            ),
        )
    return html.Div(rows, className="fxs")


def render_sports_badge(data: dict[str, Any]):
    from .data import get_summary_fixtures

    today = local_today()
    todays = [
        fx
        for fx in get_summary_fixtures(data, limit=10, days_ahead=0)
        if fixture_date(fx) == today
    ]
    if todays:
        return badge(
            f"Today {todays[0].get('time', '')}".strip(), "good", "mdi:television-play"
        )
    return None
