import datetime
from typing import Any

from dash import html

from utils.dates import local_today
from utils.ui import empty_state, filter_chips

from .data import SPORTS, get_full_screen_fixtures
from .summary import crest, fixture_date


def render_sports_fullscreen(data: dict[str, Any]) -> html.Div:
    """Every upcoming fixture, grouped by day, with a per-sport filter."""
    today = local_today()
    fixtures = [
        fx
        for fx in get_full_screen_fixtures(data)
        if (fixture_date(fx) or datetime.date.max) >= today
    ]
    if not fixtures:
        return html.Div(
            empty_state("No upcoming fixtures found", "mdi:trophy-outline"),
            className="detail",
        )

    by_day: dict[datetime.date | None, list[dict[str, Any]]] = {}
    for fx in fixtures:
        by_day.setdefault(fixture_date(fx), []).append(fx)

    days = []
    for date, items in by_day.items():
        if date is None:
            title, sub = "Date to be confirmed", ""
        elif date == today:
            title, sub = "Today", f"{date:%A} {date.day} {date:%B}"
        elif date == today + datetime.timedelta(days=1):
            title, sub = "Tomorrow", f"{date:%A} {date.day} {date:%B}"
        else:
            title, sub = (
                f"{date:%A} {date.day} {date:%B}",
                f"in {(date - today).days} days",
            )
        days.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(title, className="agenda-day__title"),
                            html.Span(sub, className="agenda-day__sub"),
                        ],
                        className="agenda-day__head"
                        + (" is-today" if date == today else ""),
                    ),
                    html.Div([_fixture_row(fx) for fx in items], className="fx-rows"),
                ],
                className="agenda-day card",
                **{"data-filter-scope": ""},
            ),
        )

    sport_options = [
        ((s.display_name or s.url.title()).lower(), s.display_name or s.url.title())
        for s in SPORTS
    ]
    return html.Div(
        [filter_chips("sport", sport_options), html.Div(days, className="agenda")],
        className="detail",
    )


def _fixture_row(fx: dict[str, Any]) -> html.Div:
    return html.Div(
        [
            crest(fx),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(fx.get("home", ""), className="fx-row__team"),
                            html.Span("v", className="fx-row__v"),
                            html.Span(fx.get("away", ""), className="fx-row__team"),
                        ],
                        className="fx-row__teams",
                    ),
                    html.Div(
                        " · ".join(
                            p
                            for p in (
                                fx.get("sport_name", ""),
                                fx.get("competition", ""),
                            )
                            if p
                        ),
                        className="fx-row__comp",
                    ),
                ],
                className="fx-row__text",
            ),
            html.Div(
                [
                    html.Div(fx.get("time") or "TBC", className="fx-row__time"),
                    html.Div(fx.get("channel", ""), className="fx-row__channel")
                    if fx.get("channel")
                    else None,
                ],
                className="fx-row__right",
            ),
        ],
        className="fx-row",
        **{"data-filter-key": (fx.get("sport_name") or "").lower()},
    )
