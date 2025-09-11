import datetime
from typing import Any

from dash import html
from dash_iconify import DashIconify

from utils.dates import _opacity_from_days_away
from utils.styles import COLORS, FONT_SIZES


def render_sports_summary(data: dict[str, Any], component_id: str) -> html.Div:
    """Render the sports summary view with next 3 fixtures in 7 days."""
    from .data import get_summary_fixtures

    fixtures = get_summary_fixtures(data)

    if not fixtures:
        return html.Div(
            "No upcoming fixtures",
            style={
                "color": COLORS["soft_gray"],
                "textAlign": "center",
                "padding": "1rem",
                "fontSize": FONT_SIZES["summary_primary"],
                # inherit font
            },
        )

    fixture_cards = []
    today = datetime.date.today()

    for fx in fixtures:
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
            except ValueError:
                date_display = fx.get("date_time_raw", "")[:20]

        crest = fx.get("crest")

        # Create compact fixture card
        fixture_card = html.Div(
            [
                html.Div(
                    [
                        # Left side: sport icon and teams
                        html.Div(
                            [
                                DashIconify(
                                    icon=fx.get("sport_icon", "mdi:help-circle"),
                                    style={
                                        "marginRight": "8px",
                                        "color": fx.get(
                                            "sport_icon_color",
                                            COLORS["blue"],
                                        ),
                                        "flexShrink": "0",
                                        "fontSize": FONT_SIZES["summary_heading"],
                                        "display": "none" if crest else "block",
                                    },
                                ),
                                html.Img(
                                    src=crest,
                                    style={
                                        "height": "34px",
                                        "width": "34px",
                                        "objectFit": "contain",
                                        "marginRight": "8px",
                                        "display": "block" if crest else "none",
                                        "filter": "drop-shadow(0 0 2px rgba(0,0,0,0.6))",
                                    },
                                ),
                                html.Span(
                                    f"{fx.get('home', '?')} vs {fx.get('away', '?')}",
                                    style={
                                        "fontWeight": "600" if is_today else "500",
                                        "color": COLORS["white"],
                                        "flex": "1",
                                        "textOverflow": "ellipsis",
                                        "whiteSpace": "nowrap",
                                        "fontSize": FONT_SIZES["summary_primary"],
                                        # inherit font
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "flex": "1",
                                "minWidth": "0",
                            },
                        ),
                        # Right side: date and time
                        html.Div(
                            [
                                html.Span(
                                    date_display,
                                    style={
                                        "color": COLORS["gold"]
                                        if is_today
                                        else COLORS["soft_gray"],
                                        "fontWeight": "600" if is_today else "400",
                                        "marginRight": "6px",
                                        "fontSize": FONT_SIZES["summary_secondary"],
                                        # inherit font
                                    },
                                ),
                                html.Span(
                                    fx.get("time", ""),
                                    style={
                                        "color": COLORS["orange"],
                                        "fontWeight": "500",
                                        "fontSize": FONT_SIZES["summary_secondary"],
                                        # inherit font
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
                "border": f"2px solid {COLORS['gold']}"
                if is_today
                else None,#"1px solid rgba(255,255,255,0.12)",
                "borderRadius": "8px",
                "padding": "0px 14px",
                "marginBottom": "3px",
                "fontSize": FONT_SIZES["summary_secondary"],
                # inherit font
                "opacity": _opacity_from_days_away(date_obj),
            },
        )

        fixture_cards.append(fixture_card)

    return html.Div(
        fixture_cards,
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "6px",
            "width": "100%",
            # inherit font
        },
    )
