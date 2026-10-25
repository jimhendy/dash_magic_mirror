from typing import Any

from dash import html

from utils.ui import empty_state


def render_news_summary(items: list[dict[str, Any]]) -> html.Div:
    """Headlines stacked in one slot; assets/dashboard.js cycles through
    them (`data-rotate`) client-side, no server round-trip.
    """
    if not items:
        return empty_state("No headlines right now", "mdi:newspaper-variant-outline")
    return html.Div(
        [
            html.Div(
                [
                    html.Div(item["title"], className="news__title"),
                    html.Div(item.get("source", ""), className="news__source"),
                ],
                className="news" + (" is-active" if index == 0 else ""),
            )
            for index, item in enumerate(items)
        ],
        className="news-rotator",
        **{"data-rotate": ""},
    )
