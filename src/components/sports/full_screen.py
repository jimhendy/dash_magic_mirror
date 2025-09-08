import datetime
from typing import Any

from dash import dcc, html
from dash_iconify import DashIconify

from utils.styles import COLORS, FONT_FAMILY

from .data import SPORTS, get_full_screen_fixtures


def render_sports_fullscreen(data: dict[str, Any], component_id: str) -> html.Div:
    """Render the sports full screen view with detailed fixture information including filter controls."""
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

    # Build filter options
    filter_options = [
        {"label": "All", "value": "all"},
    ]
    for sport in SPORTS:
        label = sport.display_name or sport.url.title()
        filter_options.append({"label": label, "value": label.lower()})

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

        row = {
            "Sport": fx.get("sport_name", ""),
            "Date": date_display,
            "Time": fx.get("time", ""),
            "Home": fx.get("home", ""),
            "Away": fx.get("away", ""),
            "Competition": fx.get("competition", ""),
            "Channel": fx.get("channel", ""),
            "Crest": fx.get("crest"),  # new
            "_is_today": is_today,
            "_sport_icon": fx.get("sport_icon", "mdi:help-circle"),
            "_sport_color": fx.get("sport_icon_color", COLORS["blue"]),
        }
        table_data.append(row)

    fixture_cards = []
    for idx, row in enumerate(table_data):
        is_today = row["_is_today"]
        sport_value = row["Sport"].lower()

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
                                        "display": "none"
                                        if row.get("Crest")
                                        else "block",
                                    },
                                ),
                                html.Img(
                                    src=row.get("Crest"),
                                    style={
                                        "height": "34px",
                                        "width": "34px",
                                        "objectFit": "contain",
                                        "marginRight": "10px",
                                        "display": "block"
                                        if row.get("Crest")
                                        else "none",
                                        "filter": "drop-shadow(0 0 2px rgba(0,0,0,0.6))",
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
            id=f"{component_id}-fixture-card-{idx}",
            **{"data-sport": sport_value},
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
            # Filter bar
            html.Div(
                [
                    dcc.RadioItems(
                        id=f"{component_id}-sport-filter",
                        options=filter_options,
                        value="all",
                        inline=True,
                        labelStyle={
                            "marginRight": "12px",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "4px",
                        },
                        style={
                            "fontFamily": FONT_FAMILY,
                            "fontSize": "0.9rem",
                            "display": "flex",
                            "flexWrap": "wrap",
                            "gap": "16px",
                            "color": COLORS["white"],
                            "marginBottom": "6px",
                            "justifyContent": "center",  # centered buttons
                            "width": "100%",
                        },
                    ),
                ],
                style={
                    "padding": "8px 10px 4px 10px",
                    "borderBottom": f"1px solid {COLORS['soft_gray']}",
                    "marginBottom": "10px",
                    "display": "flex",
                    "justifyContent": "center",
                },
            ),
            # Fixtures wrapper
            html.Div(
                fixture_cards,
                id=f"{component_id}-fixtures-wrapper",
                style={"padding": "0 20px"},
            ),
        ],
        style={
            "color": COLORS["white"],
            "fontFamily": FONT_FAMILY,
        },
    )
