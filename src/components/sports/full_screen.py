import datetime
from typing import Any

from dash import dcc, html
from dash_iconify import DashIconify

from utils.dates import local_today
from utils.styles import COLORS, WEIGHT, row_style

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
                        "color": COLORS["text_secondary"],
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
    today = local_today()

    for fx in fixtures:
        # Format date
        date_display = ""
        is_today = False

        if fx.get("parsed_date"):
            try:
                date_obj = datetime.date.fromisoformat(fx["parsed_date"])
                if date_obj < today:
                    continue  # Skip past fixtures
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
            "Crest": fx.get("crest"),
            "_is_today": is_today,
            "_sport_icon": fx.get("sport_icon", "mdi:help-circle"),
            "_sport_color": fx.get("sport_icon_color", COLORS["text_secondary"]),
        }
        table_data.append(row)

    fixture_rows = []
    for idx, row in enumerate(table_data):
        is_today = row["_is_today"]
        sport_value = row["Sport"].lower()

        fixture_rows.append(
            html.Div(
                [
                    # Left: sport icon/crest + teams
                    html.Div(
                        [
                            DashIconify(
                                icon=row["_sport_icon"],
                                style={
                                    "color": row["_sport_color"],
                                    "fontSize": "1.4rem",
                                    "display": "none" if row.get("Crest") else "block",
                                },
                            ),
                            html.Img(
                                src=row.get("Crest"),
                                style={
                                    "height": "1.875rem",
                                    "width": "1.875rem",
                                    "objectFit": "contain",
                                    "display": "block" if row.get("Crest") else "none",
                                },
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        f"{row['Home']} vs {row['Away']}",
                                        style={
                                            "fontSize": "1.25rem",
                                            "fontWeight": WEIGHT["semibold"],
                                            "color": COLORS["text"],
                                        },
                                    ),
                                    html.Div(
                                        f"{row['Sport']} · {row['Competition']}",
                                        style={
                                            "fontSize": "0.9rem",
                                            "color": COLORS["text_muted"],
                                            "marginTop": "0.15rem",
                                        },
                                    ),
                                ],
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "0.7rem",
                            "flex": "1",
                        },
                    ),
                    # Right: date/time/channel
                    html.Div(
                        [
                            html.Span(
                                row["Date"],
                                style={
                                    "color": COLORS["accent"]
                                    if is_today
                                    else COLORS["text"],
                                    "fontWeight": WEIGHT["semibold"],
                                    "fontSize": "1.1rem",
                                    "marginRight": "0.9rem",
                                },
                            ),
                            html.Span(
                                row["Time"],
                                style={
                                    "color": COLORS["gold"],
                                    "fontWeight": WEIGHT["semibold"],
                                    "fontSize": "1.05rem",
                                    "marginRight": "0.9rem",
                                },
                            ),
                            html.Span(
                                row["Channel"],
                                style={
                                    "color": COLORS["text_muted"],
                                    "fontSize": "0.9rem",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "whiteSpace": "nowrap",
                        },
                    ),
                ],
                id=f"{component_id}-fixture-card-{idx}",
                **{"data-sport": sport_value},
                style=row_style(
                    divider=True,
                    display="flex",
                    alignItems="center",
                    justifyContent="space-between",
                    padding="0.8rem 0",
                    borderLeft=f"2px solid {COLORS['accent']}"
                    if is_today
                    else "2px solid transparent",
                ),
            ),
        )

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
                            "marginRight": "0.75rem",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "0.25rem",
                        },
                        style={
                            "fontSize": "0.9rem",
                            "display": "flex",
                            "flexWrap": "wrap",
                            "gap": "1rem",
                            "color": COLORS["text"],
                            "justifyContent": "center",
                            "width": "100%",
                        },
                    ),
                ],
                style={
                    "position": "sticky",
                    "top": "0",
                    "zIndex": 1,
                    "background": COLORS["bg"],
                    "padding": "0.6rem 0.6rem 0.3rem 0.6rem",
                    "borderBottom": f"1px solid {COLORS['hairline_strong']}",
                    "marginBottom": "0.6rem",
                    "display": "flex",
                    "justifyContent": "center",
                },
            ),
            # Fixtures wrapper
            html.Div(
                fixture_rows,
                id=f"{component_id}-fixtures-wrapper",
                style={"padding": "0 1rem"},
            ),
        ],
        style={"color": COLORS["text"]},
    )
