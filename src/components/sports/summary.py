import datetime
from typing import Any

from dash import html
from dash_iconify import DashIconify

from utils.dates import _opacity_from_days_away, local_today
from utils.styles import COLORS, FONT_SIZES, WEIGHT, kicker_style, row_style


def render_sports_summary(data: dict[str, Any], component_id: str) -> html.Div:
    """Render the sports summary view with next 3 fixtures in 7 days."""
    from .data import get_summary_fixtures

    fixtures = get_summary_fixtures(data)

    if not fixtures:
        return html.Div(
            [
                html.Div("Sports", style=kicker_style()),
                html.Div(
                    "No upcoming fixtures",
                    style={
                        "color": COLORS["text_muted"],
                        "fontSize": FONT_SIZES["primary"],
                        "padding": "0.4rem 0",
                    },
                ),
            ],
            style={"display": "flex", "flexDirection": "column", "gap": "0.4rem"},
        )

    today = local_today()
    fixture_rows = []

    for fx in fixtures:
        date_display = ""
        is_today = False
        date_obj = None

        if fx.get("parsed_date"):
            try:
                date_obj = datetime.date.fromisoformat(fx["parsed_date"])
                is_today = date_obj == today
                date_display = "TODAY" if is_today else date_obj.strftime("%a %d %b")
            except ValueError:
                date_display = fx.get("date_time_raw", "")[:20]

        crest = fx.get("crest")

        fixture_rows.append(
            html.Div(
                [
                    html.Div(
                        [
                            DashIconify(
                                icon=fx.get("sport_icon", "mdi:help-circle"),
                                style={
                                    "color": fx.get(
                                        "sport_icon_color", COLORS["text_secondary"],
                                    ),
                                    "flexShrink": "0",
                                    "fontSize": FONT_SIZES["heading"],
                                    "display": "none" if crest else "block",
                                },
                            ),
                            html.Img(
                                src=crest,
                                style={
                                    "height": "2.125rem",
                                    "width": "2.125rem",
                                    "objectFit": "contain",
                                    "display": "block" if crest else "none",
                                },
                            ),
                            html.Span(
                                f"{fx.get('home', '?')} vs {fx.get('away', '?')}",
                                style={
                                    "fontWeight": WEIGHT["semibold"]
                                    if is_today
                                    else WEIGHT["regular"],
                                    "color": COLORS["text"],
                                    "fontSize": FONT_SIZES["primary"],
                                    "overflow": "hidden",
                                    "textOverflow": "ellipsis",
                                    "whiteSpace": "nowrap",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "0.6rem",
                            "flex": "1",
                            "minWidth": "0",
                        },
                    ),
                    html.Div(
                        [
                            html.Span(
                                date_display,
                                style={
                                    "color": COLORS["accent"]
                                    if is_today
                                    else COLORS["text_secondary"],
                                    "fontWeight": WEIGHT["semibold"]
                                    if is_today
                                    else WEIGHT["regular"],
                                    "fontSize": FONT_SIZES["secondary"],
                                },
                            ),
                            html.Span(
                                fx.get("time", ""),
                                style={
                                    "color": COLORS["gold"],
                                    "fontWeight": WEIGHT["semibold"],
                                    "fontSize": FONT_SIZES["secondary"],
                                    "marginLeft": "0.5rem",
                                },
                            ),
                        ],
                        style={"whiteSpace": "nowrap"},
                    ),
                ],
                style=row_style(
                    divider=True,
                    display="flex",
                    alignItems="center",
                    justifyContent="space-between",
                    opacity=_opacity_from_days_away(date_obj),
                    borderLeft=f"2px solid {COLORS['accent']}"
                    if is_today
                    else "2px solid transparent",
                ),
            ),
        )

    return html.Div(
        [html.Div("Sports", style=kicker_style()), *fixture_rows],
        style={"display": "flex", "flexDirection": "column", "gap": "0.2rem"},
    )
