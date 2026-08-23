from typing import Any

from dash import html
from dash_iconify import DashIconify

from utils.models import FullScreenResult
from utils.styles import COLORS, FONT_SIZES, SPACE, row_style


def _news_item(item: dict[str, Any]) -> html.Div:
    return html.Div(
        [
            DashIconify(
                icon="mdi:newspaper-variant-outline",
                color=COLORS["text_muted"],
                style={
                    "width": "1.25rem",
                    "height": "1.25rem",
                    "flexShrink": 0,
                    "marginTop": "0.25rem",
                },
            ),
            html.Div(
                [
                    html.Div(
                        item["title"],
                        style={
                            "color": COLORS["text"],
                            "fontSize": FONT_SIZES["primary"],
                            "fontWeight": "500",
                        },
                    ),
                    html.Div(
                        item["source"],
                        style={
                            "color": COLORS["text_muted"],
                            "fontSize": FONT_SIZES["small"],
                            "marginTop": SPACE["xs"],
                        },
                    ),
                ],
                style={"flex": "1", "minWidth": 0},
            ),
        ],
        style=row_style(divider=True, display="flex", gap=SPACE["sm"]),
        className="mm-list-item",
    )


def render_news_fullscreen(
    items: list[dict[str, Any]], component_id: str,
) -> FullScreenResult:
    if not items:
        content = html.Div(
            "No headlines available",
            style={"color": COLORS["text_muted"], "padding": SPACE["xl"]},
        )
    else:
        content = html.Div(
            [_news_item(item) for item in items],
            id=f"{component_id}-fullscreen-list",
            style={"padding": SPACE["xl"], "overflowY": "auto", "height": "100%"},
            className="hidden-scrollbar",
        )
    return FullScreenResult(content=content, title="Headlines")
