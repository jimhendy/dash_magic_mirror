from typing import Any

from dash import html

from utils.styles import COLORS, FONT_SIZES, kicker_style


def render_news_summary(items: list[dict[str, Any]], component_id: str) -> html.Div:
    """Render a kicker label plus a single rotating headline. All headlines
    are present in the DOM; a clientside interval (wired in
    `News._add_callbacks`) toggles which one is visible, so rotation needs
    no server round-trip.
    """
    if not items:
        return html.Div(
            [
                html.Div("News", style=kicker_style()),
                html.Div(
                    "No headlines available",
                    style={
                        "color": COLORS["text_muted"],
                        "fontSize": FONT_SIZES["secondary"],
                    },
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "0.4rem"},
        )

    headline_rows = [
        html.Div(
            [
                html.Span(
                    item["title"],
                    style={
                        "color": COLORS["text"],
                        "fontWeight": "500",
                        "fontSize": FONT_SIZES["secondary"],
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                    },
                ),
                html.Span(
                    item["source"],
                    style={
                        "color": COLORS["text_muted"],
                        "marginLeft": "0.5rem",
                        "fontSize": FONT_SIZES["small"],
                        "flexShrink": 0,
                    },
                ),
            ],
            **{"data-headline-index": str(i)},
            style={
                "display": "flex" if i == 0 else "none",
                "alignItems": "baseline",
                "minWidth": 0,
                "width": "100%",
            },
        )
        for i, item in enumerate(items)
    ]

    return html.Div(
        [
            html.Div("News", style=kicker_style()),
            html.Div(
                headline_rows,
                id=f"{component_id}-headlines-wrapper",
                style={"width": "100%", "overflow": "hidden"},
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "0.35rem",
            "width": "100%",
        },
    )
