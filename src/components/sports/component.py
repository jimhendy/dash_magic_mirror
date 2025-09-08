from dash import Input, Output, State, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.models import FullScreenResult
from utils.styles import FONT_FAMILY

from .data import process_sports_data
from .full_screen import render_sports_fullscreen
from .summary import render_sports_summary


class Sports(BaseComponent):
    """Sports component for the Magic Mirror application.

    Displays upcoming sports fixtures for configured teams.

    Summary view: Shows next 3 fixtures within 7 days
    Full screen view: Shows all fixtures with detailed information including competition and channel

    Configuration is done in data.py SPORTS list.
    """

    def __init__(self, fetch_minutes: int = 360, **kwargs):
        # Enable preloaded full screen path
        super().__init__(name="sports", preloaded_full_screen=True, **kwargs)
        self.fetch_minutes = fetch_minutes

    def _summary_layout(self):
        """Returns the layout of the Sports component."""
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval-fetch",
                    interval=self.fetch_minutes
                    * 60_000,  # Convert minutes to milliseconds
                    n_intervals=0,
                ),
                dcc.Store(id=f"{self.component_id}-store", data=None),
                # New hidden stores for full screen prepopulation
                dcc.Store(id=f"{self.component_id}-fullscreen-title-store", data=None),
                dcc.Store(
                    id=f"{self.component_id}-fullscreen-content-store",
                    data=None,
                ),
                html.Div(
                    id=f"{self.component_id}-content",
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "stretch",
                        "gap": "8px",
                        "width": "100%",
                        "color": "#FFFFFF",
                    },
                ),
            ],
        )

    def _add_callbacks(self, app):
        """Add callbacks for the Sports component."""

        @app.callback(
            Output(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
            prevent_initial_call=False,
        )
        def update_sports_data(_n):
            try:
                return process_sports_data()
            except Exception as e:
                logger.error(f"Error fetching sports fixtures: {e}")
                return {}

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Input(f"{self.component_id}-store", "data"),
            prevent_initial_call=False,
        )
        def render_sports_summary_view(data):
            try:
                return render_sports_summary(data, self.component_id)
            except Exception as e:
                logger.error(f"Error rendering sports summary: {e}")
                return html.Div(
                    "Sports unavailable",
                    style={
                        "color": "#FF6B6B",
                        "textAlign": "center",
                        "padding": "1rem",
                        "fontSize": "1.1rem",
                        "fontFamily": FONT_FAMILY,
                    },
                )

        # Populate full screen stores whenever data updates or on first click if not yet populated
        @app.callback(
            Output(f"{self.component_id}-fullscreen-title-store", "data"),
            Output(f"{self.component_id}-fullscreen-content-store", "data"),
            Input(f"{self.component_id}-store", "data"),
            State(f"{self.component_id}-fullscreen-title-store", "data"),
            prevent_initial_call=False,
        )
        def populate_fullscreen_stores(data, existing_title):
            try:
                # If no data yet
                if not data:
                    return existing_title, existing_title  # leave unchanged / None
                content = render_sports_fullscreen(data, self.component_id)
                # Title is static string for this component
                title = html.Div(
                    "Sports Fixtures",
                    className="text-m",
                    **{"data-component-name": self.name},
                )
                return title, content
            except Exception as e:
                logger.error(f"Error preparing sports full screen: {e}")
                return existing_title, existing_title

    def full_screen_content(self) -> FullScreenResult:
        """Fallback path (not used in preloaded mode)."""
        try:
            data = process_sports_data()
            content = render_sports_fullscreen(data, self.component_id)
            return FullScreenResult(content=content, title="Sports Fixtures")
        except Exception as e:
            logger.error(f"Error loading full-screen sports: {e}")
            return FullScreenResult(
                content=html.Div(
                    "Sports fixtures unavailable",
                    style={
                        "color": "#FF6B6B",
                        "textAlign": "center",
                        "padding": "2rem",
                        "fontSize": "1.5rem",
                        "fontFamily": FONT_FAMILY,
                    },
                ),
                title="Sports unavailable",
            )
