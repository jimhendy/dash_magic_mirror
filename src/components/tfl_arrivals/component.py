from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.models import FullScreenResult
from utils.styles import FONT_FAMILY

from .data import (
    fetch_arrivals_for_stop,
    fetch_line_status,
    fetch_stoppoint_disruptions,
    get_all_stop_ids,
    get_primary_stop_id,
    process_arrivals_data,
    process_line_status_data,
    process_stoppoint_disruptions,
)
from .full_screen import render_tfl_fullscreen
from .summary import render_tfl_summary


class TFLArrivals(BaseComponent):
    """TFL Arrivals component for the Magic Mirror application.

    Displays train/bus arrivals for TFL services with line status and station disruption information.

    Summary view: Shows next 2 departures from TFL_STOP_ID_1 with status indicators
    Full screen view: Shows all arrivals from all configured stops with status tables

    Environment variables required:
    - TFL_STOP_ID_1: Primary stop ID for summary view
    - TFL_STOP_ID_2, TFL_STOP_ID_3, etc.: Additional stops for full screen view

    Stop IDs can be found using: https://api.tfl.gov.uk/StopPoint/Search/<search_term>
    E.g. https://api.tfl.gov.uk/StopPoint/Search/Waterloo
    """

    def __init__(self, **kwargs):
        super().__init__(name="tfl_arrivals", preloaded_full_screen=True, **kwargs)

        # Get stop IDs from environment
        self.all_stop_ids = get_all_stop_ids()
        self.primary_stop_id = get_primary_stop_id()

        if not self.primary_stop_id:
            logger.warning(
                "TFL_STOP_ID_1 not set - TFL component may not work correctly",
            )

    def _summary_layout(self):
        """Returns the layout of the TFL Arrivals component summary."""
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=30 * 1000,  # Update every 30 seconds
                    n_intervals=0,
                ),
                dcc.Interval(
                    id=f"{self.component_id}-fullscreen-interval",
                    interval=30 * 1000,  # Update every 30 seconds
                    n_intervals=0,
                ),
                dcc.Store(id=f"{self.component_id}-fullscreen-title-store", data=None),
                dcc.Store(
                    id=f"{self.component_id}-fullscreen-content-store",
                    data=None,
                ),
                html.Div(
                    id=f"{self.component_id}-content",
                    style={
                        "color": "#FFFFFF",
                        "fontSize": "16px",  # Increased from 14px
                        "fontFamily": FONT_FAMILY,
                    },
                ),
            ],
        )

    def _fullscreen_layout(self):
        """Returns the layout of the TFL Arrivals component full screen."""
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-fullscreen-interval",
                    interval=30 * 1000,  # Update every 30 seconds
                    n_intervals=0,
                ),
                html.Div(
                    id=f"{self.component_id}-fullscreen-content",
                ),
            ],
        )

    def _get_summary_data(self):
        """Get data for summary view (primary stop only)."""
        if not self.primary_stop_id:
            return {}, {}, {}

        # Fetch arrivals for primary stop
        arrivals = fetch_arrivals_for_stop(self.primary_stop_id)
        arrivals_data = process_arrivals_data(arrivals, is_summary=True)

        # Fetch line status
        line_ids = arrivals_data.get("line_ids", [])
        line_status_raw = fetch_line_status(line_ids) if line_ids else []
        line_status = process_line_status_data(line_status_raw)

        # Fetch stop disruptions
        stop_disruptions_raw = fetch_stoppoint_disruptions([self.primary_stop_id])
        stop_disruptions = process_stoppoint_disruptions(stop_disruptions_raw)

        return arrivals_data, line_status, stop_disruptions

    def _get_fullscreen_data(self):
        """Get data for full screen view (all stops)."""
        if not self.all_stop_ids:
            return {}, {}, {}

        # Fetch arrivals for all stops
        all_arrivals_data = {}
        all_line_ids = set()

        for stop_id in self.all_stop_ids:
            arrivals = fetch_arrivals_for_stop(stop_id)
            arrivals_data = process_arrivals_data(arrivals, is_summary=False)
            all_arrivals_data[stop_id] = arrivals_data
            all_line_ids.update(arrivals_data.get("line_ids", []))

        # Fetch line status for all lines
        line_status_raw = fetch_line_status(list(all_line_ids)) if all_line_ids else []
        line_status = process_line_status_data(line_status_raw)

        # Fetch stop disruptions for all stops
        stop_disruptions_raw = fetch_stoppoint_disruptions(self.all_stop_ids)
        stop_disruptions = process_stoppoint_disruptions(stop_disruptions_raw)

        return all_arrivals_data, line_status, stop_disruptions

    def _add_callbacks(self, app):
        # Summary callback
        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Input(f"{self.component_id}-interval", "n_intervals"),
        )
        def update_tfl_summary(_):
            try:
                arrivals_data, line_status, stop_disruptions = self._get_summary_data()
                return render_tfl_summary(arrivals_data, line_status, stop_disruptions)
            except Exception as e:
                logger.error(f"Error updating TFL summary: {e}")
                return html.Div(
                    "Transport data unavailable",
                    style={
                        "color": "#999999",
                        "textAlign": "center",
                        "padding": "20px",
                        "fontFamily": FONT_FAMILY,
                    },
                )

        # Populate full screen stores using fullscreen interval
        @app.callback(
            Output(f"{self.component_id}-fullscreen-title-store", "data"),
            Output(f"{self.component_id}-fullscreen-content-store", "data"),
            Input(f"{self.component_id}-fullscreen-interval", "n_intervals"),
            prevent_initial_call=False,
        )
        def populate_fullscreen(_n):
            try:
                all_arrivals_data, line_status, stop_disruptions = (
                    self._get_fullscreen_data()
                )
                content = render_tfl_fullscreen(
                    all_arrivals_data,
                    line_status,
                    stop_disruptions,
                )
                title = html.Div(
                    "Transport Arrivals",
                    className="text-m",
                    **{"data-component-name": self.name},
                )
                return title, content
            except Exception as e:
                logger.error(f"Error preparing TFL full screen: {e}")
                return None, None

        # Full screen callback
        @app.callback(
            Output(f"{self.component_id}-fullscreen-content", "children"),
            Input(f"{self.component_id}-fullscreen-interval", "n_intervals"),
        )
        def update_tfl_fullscreen(_):
            try:
                all_arrivals_data, line_status, stop_disruptions = (
                    self._get_fullscreen_data()
                )
                return render_tfl_fullscreen(
                    all_arrivals_data,
                    line_status,
                    stop_disruptions,
                )
            except Exception as e:
                logger.error(f"Error updating TFL full screen: {e}")
                return html.Div(
                    "Transport data unavailable",
                    style={
                        "color": "#999999",
                        "textAlign": "center",
                        "padding": "40px",
                        "fontSize": "1.5rem",
                        "fontFamily": FONT_FAMILY,
                    },
                )

    def full_screen_content(self) -> FullScreenResult:
        """Returns the full-screen layout of the TFL Arrivals component."""
        try:
            all_arrivals_data, line_status, stop_disruptions = (
                self._get_fullscreen_data()
            )
            content = render_tfl_fullscreen(
                all_arrivals_data,
                line_status,
                stop_disruptions,
            )
            return FullScreenResult(content=content, title="Transport Arrivals")
        except Exception as e:
            logger.error(f"Error loading full-screen TFL arrivals: {e}")
            return FullScreenResult(
                content=html.Div(
                    "Transport data unavailable",
                    style={
                        "color": "#ff6b6b",
                        "textAlign": "center",
                        "padding": "40px",
                        "fontSize": "1.5rem",
                        "fontFamily": FONT_FAMILY,
                    },
                ),
                title="Transport Unavailable",
            )
