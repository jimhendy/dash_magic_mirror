import datetime
from typing import Any

from dash import html
from dash_iconify import DashIconify

from utils.dates import _opacity_from_days_away
from utils.styles import COLORS, FONT_FAMILY


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
                "fontSize": "1.1rem",  # Increased from 0.9rem
                "fontFamily": FONT_FAMILY,
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
                                        "fontSize": "1.4rem",  # Increased from 1.2rem
                                    },
                                ),
                                html.Span(
                                    f"{fx.get('home', '?')} vs {fx.get('away', '?')}",
                                    style={
                                        "fontWeight": "bold" if is_today else "500",
                                        "color": COLORS["white"],
                                        "flex": "1",
                                        "textOverflow": "ellipsis",
                                        "whiteSpace": "nowrap",
                                        "fontSize": "1.1rem",  # Added explicit font size
                                        "fontFamily": FONT_FAMILY,
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
                                        "fontWeight": "bold" if is_today else "400",
                                        "marginRight": "6px",
                                        "fontSize": "1rem",  # Increased from 0.85rem
                                        "fontFamily": FONT_FAMILY,
                                    },
                                ),
                                html.Span(
                                    fx.get("time", ""),
                                    style={
                                        "color": COLORS["orange"],
                                        "fontWeight": "500",
                                        "fontSize": "1rem",  # Increased from 0.85rem
                                        "fontFamily": FONT_FAMILY,
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
                "border": f"1px solid {COLORS['gold']}"
                if is_today
                else "1px solid rgba(255,255,255,0.08)",
                "borderRadius": "6px",
                "padding": "8px 10px",  # Increased padding from 6px 8px
                "marginBottom": "4px",
                "backdropFilter": "blur(10px)",
                "fontSize": "1rem",  # Increased from 0.9rem
                "fontFamily": FONT_FAMILY,
                "opacity": _opacity_from_days_away(date_obj),
            },
        )

        fixture_cards.append(fixture_card)

    return html.Div(
        fixture_cards,
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "4px",
            "width": "100%",
            "fontFamily": FONT_FAMILY,
        },
    )
