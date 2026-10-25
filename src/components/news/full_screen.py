from typing import Any

from dash import html

from utils.ui import empty_state


def render_news_fullscreen(items: list[dict[str, Any]]) -> html.Div:
    if not items:
        return html.Div(
            empty_state("No headlines right now", "mdi:newspaper-variant-outline"),
            className="detail",
        )
    return html.Div(
        html.Div(
            [
                html.Div(
                    [
                        html.Div(item["title"], className="news-row__title"),
                        html.Div(item.get("source", ""), className="news-row__source"),
                    ],
                    className="news-row",
                )
                for item in items
            ],
            className="card news-rows",
        ),
        className="detail",
    )
