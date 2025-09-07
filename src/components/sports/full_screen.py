import datetime
from typing import Any

from dash import html
from dash_iconify import DashIconify

from utils.styles import COLORS, FONT_FAMILY


def render_sports_fullscreen(data: dict[str, Any], component_id: str) -> html.Div:
    """Render the sports full screen view with detailed fixture information."""
    from .data import get_full_screen_fixtures

    fixtures = get_full_screen_fixtures(data)

    if not fixtures:
        return html.Div(
            [
                html.Div(
                    "No upcoming fixtures found",
                    style={
                        "color": COLORS["soft_gray"],
                        "textAlign": "center",
                        "padding": "2rem",
                        "fontSize": "1.2rem",
                    },
                ),
            ],
        )

    # Create table data
    table_data = []
    today = datetime.date.today()

    for fx in fixtures:
        # Format date
        date_display = ""
        is_today = False

        if fx.get("parsed_date"):
            try:
                date_obj = datetime.date.fromisoformat(fx["parsed_date"])
                is_today = date_obj == today

                if is_today:
                    date_display = "TODAY"
                elif date_obj == today + datetime.timedelta(days=1):
                    date_display = "TOMORROW"
                else:
                    date_display = date_obj.strftime("%a %d %b")
            except ValueError:
                date_display = fx.get("date_time_raw", "")[:15]

        # Create row data
        row = {
            "Sport": fx.get("sport_name", ""),
            "Date": date_display,
            "Time": fx.get("time", ""),
            "Home": fx.get("home", ""),
            "Away": fx.get("away", ""),
            "Competition": fx.get("competition", ""),
            "Channel": fx.get("channel", ""),
            "_is_today": is_today,
            "_sport_icon": fx.get("sport_icon", "mdi:help-circle"),
            "_sport_color": fx.get("sport_icon_color", COLORS["blue"]),
        }
        table_data.append(row)

    # Create custom fixture cards instead of table for better formatting
    fixture_cards = []

    for row in table_data:
        is_today = row["_is_today"]

        card = html.Div(
            [
                # Header row with sport, date, time
                html.Div(
                    [
                        html.Div(
                            [
                                DashIconify(
                                    icon=row["_sport_icon"],
                                    style={
                                        "marginRight": "10px",
                                        "color": row["_sport_color"],
                                        "fontSize": "1.5rem",
                                    },
                                ),
                                html.Span(
                                    row["Sport"],
                                    style={
                                        "fontWeight": "bold",
                                        "color": COLORS["white"],
                                        "fontSize": "1.1rem",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "flex": "1",
                            },
                        ),
                        html.Div(
                            [
                                html.Span(
                                    row["Date"],
                                    style={
                                        "color": COLORS["gold"]
                                        if is_today
                                        else COLORS["soft_gray"],
                                        "fontWeight": "bold" if is_today else "500",
                                        "marginRight": "15px",
                                        "fontSize": "1rem",
                                    },
                                ),
                                html.Span(
                                    row["Time"],
                                    style={
                                        "color": COLORS["orange"],
                                        "fontWeight": "bold",
                                        "fontSize": "1.1rem",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "marginBottom": "8px",
                    },
                ),
                # Teams row
                html.Div(
                    [
                        html.Span(
                            f"{row['Home']} vs {row['Away']}",
                            style={
                                "fontSize": "1.3rem",
                                "fontWeight": "bold",
                                "color": COLORS["white"],
                            },
                        ),
                    ],
                    style={
                        "marginBottom": "8px",
                        "textAlign": "center",
                    },
                ),
                # Competition and channel row
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span(
                                    "Competition: ",
                                    style={
                                        "color": COLORS["soft_gray"],
                                        "fontWeight": "500",
                                    },
                                ),
                                html.Span(
                                    row["Competition"] or "N/A",
                                    style={
                                        "color": COLORS["blue"],
                                        "fontWeight": "500",
                                    },
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                        html.Div(
                            [
                                html.Span(
                                    "Channel: ",
                                    style={
                                        "color": COLORS["soft_gray"],
                                        "fontWeight": "500",
                                    },
                                ),
                                html.Span(
                                    row["Channel"] or "N/A",
                                    style={
                                        "color": COLORS["green"],
                                        "fontWeight": "bold",
                                    },
                                ),
                            ],
                            style={"flex": "1", "textAlign": "right"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "fontSize": "0.9rem",
                    },
                ),
            ],
            style={
                "border": f"2px solid {COLORS['gold']}"
                if is_today
                else f"1px solid {COLORS['soft_gray']}",
                "borderRadius": "10px",
                "padding": "15px",
                "marginBottom": "15px",
                "backgroundColor": "rgba(255, 255, 255, 0.05)"
                if is_today
                else "rgba(255, 255, 255, 0.02)",
                "backdropFilter": "blur(10px)",
            },
        )
        fixture_cards.append(card)

    return html.Div(
        [
            html.Div(
                fixture_cards,
                style={
                    "maxHeight": "80vh",
                    "overflowY": "auto",
                    "padding": "0 20px",
                },
            ),
        ],
        style={
            "color": COLORS["white"],
            "fontFamily": FONT_FAMILY,
        },
    )
