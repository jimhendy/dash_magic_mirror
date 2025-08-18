import datetime

import httpx
from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.file_cache import cache_json
from utils.styles import COLORS

API_URL = "https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"


@cache_json(valid_lifetime=datetime.timedelta(seconds=30))
def fetch_all_arrivals(stops: list[str]) -> list[dict]:
    """Fetch arrivals for all stops and return a combined sorted list."""
    all_arrivals = []
    for stop in stops:
        try:
            response = httpx.get(API_URL.format(stop_id=stop), timeout=10)
            if response.is_success:
                arrivals = response.json()
                if arrivals:
                    # Add stop info to each arrival
                    for arrival in arrivals:
                        arrival["stopId"] = stop
                    all_arrivals.extend(arrivals)
            else:
                logger.error(
                    f"Failed to fetch data for stop {stop}: {response.status_code}",
                )
        except httpx.RequestError as e:
            logger.error(f"Error fetching data for stop {stop}: {e}")

    # Sort all arrivals by expected arrival time
    all_arrivals.sort(key=lambda x: x.get("expectedArrival", ""))
    return all_arrivals[:15]  # Limit to 15 most imminent arrivals


class TFL(BaseComponent):
    """TFL component for the Magic Mirror application.
    Displays the next train times for given stations in a clean single-line format.

    StopPoints can be found using:
    https://api.tfl.gov.uk/StopPoint/Search/<search_term>
    E.g. https://api.tfl.gov.uk/StopPoint/Search/Waterloo
    """

    def __init__(self, stops, *args, **kwargs):
        super().__init__(name="tfl", *args, **kwargs)
        self.stops = stops

    def layout(self):
        """Returns the layout of the TFL component."""
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=30 * 1000,  # Update every 30 seconds
                    n_intervals=0,
                ),
                html.Div(
                    id=f"{self.component_id}-content",
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "stretch",
                        "gap": "8px",
                        "width": "100%",
                        "color": COLORS["pure_white"],
                        "fontFamily": "'Inter', 'Roboto', 'Segoe UI', 'Helvetica Neue', sans-serif",
                    },
                ),
            ],
        )

    @cache_json(valid_lifetime=datetime.timedelta(seconds=30))
    def fetch(self) -> list[dict]:
        """Fetch the latest TFL data."""
        return fetch_all_arrivals(self.stops)

    def add_callbacks(self, app):
        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Input(f"{self.component_id}-interval", "n_intervals"),
        )
        def update_arrivals(_):
            try:
                arrivals = self.fetch()
                if not arrivals:
                    return html.Div(
                        "No transport arrivals",
                        style={
                            "fontSize": "1.2rem",
                            "color": COLORS["soft_gray"],
                            "textAlign": "center",
                            "padding": "2rem",
                        },
                    )

                return self._render_arrivals(arrivals)
            except Exception as e:
                logger.error(f"Error updating TFL arrivals: {e}")
                return html.Div(
                    "Transport data unavailable",
                    style={"color": COLORS["soft_gray"], "textAlign": "center"},
                )

    def _render_arrivals(self, arrivals: list[dict]) -> list:
        """Render arrivals in a clean single-line format."""
        arrival_cards = []

        for arrival in arrivals:
            # Calculate time until arrival
            arrival_time = datetime.datetime.fromisoformat(
                arrival["expectedArrival"].replace("Z", "+00:00"),
            )
            now = datetime.datetime.now(datetime.UTC)
            time_diff = (arrival_time - now).total_seconds()
            minutes = max(0, int(time_diff // 60))

            # Skip arrivals that have already passed or are more than 30 minutes away
            if minutes < 0 or minutes > 30:
                continue

            # Clean station name
            station_name = arrival.get("stationName", "Unknown Station")
            station_name = station_name.replace(" Rail Station", "").replace(
                " Underground Station",
                "",
            )

            # Clean destination name
            destination = arrival.get("destinationName", "Unknown Destination")
            destination = destination.replace(" Rail Station", "").replace(
                " Underground Station",
                "",
            )

            # Line name
            line_name = arrival.get("lineName", "Unknown Line")

            # Time styling based on urgency
            if minutes < 2:
                time_color = COLORS["alert_red"]
                time_weight = "bold"
            elif minutes < 5:
                time_color = COLORS["accent_gold"]
                time_weight = "500"
            else:
                time_color = COLORS["pure_white"]
                time_weight = "400"

            # Create arrival card
            arrival_card = html.Div(
                [
                    html.Div(
                        [
                            # Station and line info on the left
                            html.Div(
                                [
                                    html.Span(
                                        station_name,
                                        style={
                                            "color": COLORS["primary_blue"],
                                            "fontWeight": "500",
                                            "fontSize": "1rem",
                                            "marginRight": "8px",
                                        },
                                    ),
                                    html.Span(
                                        line_name,
                                        style={
                                            "color": COLORS["soft_gray"],
                                            "fontSize": "0.9rem",
                                            "marginRight": "8px",
                                        },
                                    ),
                                    html.Span(
                                        f"→ {destination}",
                                        style={
                                            "color": COLORS["pure_white"],
                                            "fontSize": "1rem",
                                            "fontWeight": "300",
                                            "flex": "1",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "overflow": "hidden",
                                    "flex": "1",
                                },
                            ),
                            # Time on the right
                            html.Div(
                                f"{minutes}m" if minutes > 0 else "Due",
                                style={
                                    "color": time_color,
                                    "fontSize": "1.1rem",
                                    "fontWeight": time_weight,
                                    "marginLeft": "16px",
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
                style={
                    "background": "linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
                    "border": "1px solid rgba(255,255,255,0.08)",
                    "borderRadius": "8px",
                    "padding": "2px 4px",
                    "marginBottom": "0",
                    "backdropFilter": "blur(10px)",
                },
            )

            arrival_cards.append(arrival_card)

        return arrival_cards
