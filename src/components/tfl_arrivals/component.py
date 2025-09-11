from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent, PreloadedFullScreenMixin

from .data import (
    fetch_arrivals_for_stop,
    fetch_line_status,
    fetch_stoppoint_disruptions,
    fetch_transfer_station_arrivals,
    process_arrivals_data,
    process_line_status_data,
    process_stoppoint_disruptions,
)
from .full_screen import render_tfl_fullscreen
from .summary import render_tfl_summary


class TFLArrivals(PreloadedFullScreenMixin, BaseComponent):
    """TFL Arrivals component for the Magic Mirror application.

    Now fully parameterised; no direct environment reads in data layer.
    """

    def __init__(
        self,
        primary_stop_id: str,
        all_stop_ids: list[str],
        transfer_station_id: str = "",
        summary_ignore_destination: str = "",
        **kwargs,
    ):
        super().__init__(name="tfl_arrivals", preloaded_full_screen=True, **kwargs)
        self.primary_stop_id = primary_stop_id
        self.all_stop_ids = all_stop_ids
        self.transfer_station_id = transfer_station_id
        self.summary_ignore_destination = summary_ignore_destination
        if not self.primary_stop_id:
            logger.warning("Primary stop id not provided for TFLArrivals")

    def _summary_layout(self):
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=30 * 1000,
                    n_intervals=0,
                ),
                *self.preload_fullscreen_stores(),
                html.Div(
                    id=f"{self.component_id}-content",
                    style={
                        "color": "#FFFFFF",
                        "fontSize": "16px",
                    },
                ),
            ],
        )

    def _fullscreen_layout(self):
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-fullscreen-interval",
                    interval=30 * 1000,
                    n_intervals=0,
                ),
                html.Div(
                    id=f"{self.component_id}-fullscreen-content",
                ),
            ],
        )

    def _get_summary_data(self):
        if not self.primary_stop_id:
            return {}, {}, {}
        arrivals = fetch_arrivals_for_stop(self.primary_stop_id)
        arrivals_data = process_arrivals_data(
            arrivals,
            fetch_transfer_station_arrivals(self.transfer_station_id),
            self.transfer_station_id,
            self.summary_ignore_destination,
            is_summary=True,
        )
        line_ids = arrivals_data.get("line_ids", [])
        line_status_raw = fetch_line_status(line_ids) if line_ids else []
        line_status = process_line_status_data(line_status_raw)
        stop_disruptions_raw = fetch_stoppoint_disruptions([self.primary_stop_id])
        stop_disruptions = process_stoppoint_disruptions(stop_disruptions_raw)
        return arrivals_data, line_status, stop_disruptions

    def _get_fullscreen_data(self):
        if not self.all_stop_ids:
            return {}, {}, {}
        all_arrivals_data = {}
        all_line_ids = set()
        transfer_station_arrivals = fetch_transfer_station_arrivals(
            self.transfer_station_id,
        )
        for stop_id in self.all_stop_ids:
            arrivals = fetch_arrivals_for_stop(stop_id)
            arrivals_data = process_arrivals_data(
                arrivals,
                transfer_station_arrivals,
                self.transfer_station_id,
                self.summary_ignore_destination,
                is_summary=False,
            )
            all_arrivals_data[stop_id] = arrivals_data
            all_line_ids.update(arrivals_data.get("line_ids", []))
        line_status_raw = fetch_line_status(list(all_line_ids)) if all_line_ids else []
        line_status = process_line_status_data(line_status_raw)
        stop_disruptions_raw = fetch_stoppoint_disruptions(self.all_stop_ids)
        stop_disruptions = process_stoppoint_disruptions(stop_disruptions_raw)
        return all_arrivals_data, line_status, stop_disruptions

    def _add_callbacks(self, app):
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
                    },
                )

        @app.callback(
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval", "n_intervals"),
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
                    "Transport",
                    className="text-m",
                    **{"data-component-name": self.name},
                )
                return title, content
            except Exception as e:
                logger.error(f"Error preparing TFL full screen: {e}")
                return None, None
