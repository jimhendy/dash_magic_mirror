import asyncio

from dash import Input, Output, dcc, html, no_update
from loguru import logger

from components.base import BaseComponent, PreloadedFullScreenMixin
from utils.data_repository import ComponentPayload, get_repository

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
        line_status_ids: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(name="tfl_arrivals", preloaded_full_screen=True, **kwargs)
        self.primary_stop_id = primary_stop_id
        self.all_stop_ids = all_stop_ids
        self.transfer_station_id = transfer_station_id
        self.summary_ignore_destination = summary_ignore_destination
        self._line_status_ids = list(line_status_ids or [])
        if not self.primary_stop_id:
            logger.warning("Primary stop id not provided for TFLArrivals")
        self._repository = get_repository()
        self._data_key = self.name
        self._refresh_seconds = 30
        try:
            self._repository.register_component(
                self._data_key,
                refresh_coro=self._build_payload,
                interval_seconds=self._refresh_seconds,
                jitter_seconds=10,
            )
            self._initial_payload = self._repository.refresh_now_sync(self._data_key)
        except ValueError:
            self._initial_payload = self._repository.get_payload_snapshot(
                self._data_key,
            )

    async def _build_payload(self) -> ComponentPayload | None:
        return await asyncio.to_thread(self._compute_payload_sync)

    def _compute_payload_sync(self) -> ComponentPayload:
        if not self.primary_stop_id:
            return ComponentPayload(
                summary=self._build_placeholder("Transport stop not configured"),
            )

        try:
            summary_arrivals, line_status, stop_disruptions = self._get_summary_data()
            summary_children = render_tfl_summary(
                summary_arrivals,
                line_status,
                stop_disruptions,
            )

            all_arrivals, fs_line_status, fs_disruptions = self._get_fullscreen_data()
            fullscreen_content = render_tfl_fullscreen(
                all_arrivals,
                fs_line_status,
                fs_disruptions,
                self.component_id,
            )

        except Exception:  # noqa: BLE001
            logger.exception("Error building TFL payload")
            return ComponentPayload(
                summary=self._build_placeholder("Transport data unavailable"),
            )

        title = html.Div(
            "Transport",
            className="text-m",
            **{"data-component-name": self.name},
        )

        return ComponentPayload(
            summary=summary_children,
            fullscreen_title=title,
            fullscreen_content=fullscreen_content,
            raw={
                "summary": summary_arrivals,
                "summary_status": line_status,
                "summary_disruptions": stop_disruptions,
                "full": all_arrivals,
                "full_status": fs_line_status,
                "full_disruptions": fs_disruptions,
            },
        )

    def _build_placeholder(self, message: str) -> html.Div:
        return html.Div(
            message,
            style={
                "color": "#999999",
                "textAlign": "center",
                "padding": "1rem",
                "fontSize": "1.1rem",
            },
        )

    def _latest_payload(self) -> ComponentPayload | None:
        return (
            self._repository.get_payload_snapshot(self._data_key)
            or self._initial_payload
        )

    def _summary_layout(self):
        payload = self._latest_payload()
        summary_children = (
            payload.summary
            if payload and payload.summary is not None
            else self._build_placeholder("Loading transport data...")
        )
        stores = self.preload_fullscreen_stores(
            title=payload.fullscreen_title if payload else None,
            content=payload.fullscreen_content if payload else None,
        )
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval",
                    interval=self._refresh_seconds * 1000,
                    n_intervals=0,
                ),
                *stores,
                html.Div(
                    id=f"{self.component_id}-content",
                    children=summary_children,
                    style={
                        "color": "#FFFFFF",
                        "fontSize": "16px",
                    },
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
        if self._line_status_ids:
            line_ids = list(self._line_status_ids)
        else:
            line_ids = arrivals_data.get("line_ids", [])

        arrivals_data["line_ids"] = line_ids
        line_status_raw = fetch_line_status(line_ids) if line_ids else []
        line_status = process_line_status_data(line_status_raw)
        stop_disruptions_raw = fetch_stoppoint_disruptions([self.primary_stop_id])
        stop_disruptions = process_stoppoint_disruptions(stop_disruptions_raw)
        return arrivals_data, line_status, stop_disruptions

    def _get_fullscreen_data(self):
        if not self.all_stop_ids:
            return {}, {}, {}
        all_arrivals_data = {}
        all_line_ids = set(self._line_status_ids or [])
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
            if self._line_status_ids:
                line_ids = list(self._line_status_ids)
            else:
                line_ids = arrivals_data.get("line_ids", [])

            arrivals_data["line_ids"] = line_ids

            all_arrivals_data[stop_id] = arrivals_data
            all_line_ids.update(line_ids)
        line_status_raw = fetch_line_status(list(all_line_ids)) if all_line_ids else []
        line_status = process_line_status_data(line_status_raw)
        stop_disruptions_raw = fetch_stoppoint_disruptions(self.all_stop_ids)
        stop_disruptions = process_stoppoint_disruptions(stop_disruptions_raw)
        return all_arrivals_data, line_status, stop_disruptions

    def _add_callbacks(self, app):
        repo = self._repository
        data_key = self._data_key

        @app.callback(
            Output(f"{self.component_id}-content", "children"),
            Output(self.fullscreen_title_store_id(), "data"),
            Output(self.fullscreen_content_store_id(), "data"),
            Input(f"{self.component_id}-interval", "n_intervals"),
            prevent_initial_call=False,
        )
        async def hydrate_tfl(_n):
            payload = await repo.get_payload_async(data_key)
            if payload is not None:
                self._initial_payload = payload
            else:
                payload = self._latest_payload()

            if payload is None:
                placeholder = self._build_placeholder("Transport data unavailable")
                return placeholder, no_update, no_update

            return (
                payload.summary,
                payload.fullscreen_title,
                payload.fullscreen_content,
            )

        # Client-side filtering of arrivals rows by selected line
        app.clientside_callback(
            "function(value){\n  try {\n    const wrapper = document.getElementById('"
            f"{self.component_id}-arrivals-wrapper"
            "');\n    if(!wrapper){return window.dash_clientside.no_update;}\n    const rows = wrapper.querySelectorAll('[data-line]');\n    if(!rows.length){return window.dash_clientside.no_update;}\n    const sel = (value || 'all').toLowerCase();\n    rows.forEach(r=>{\n      const line = (r.getAttribute('data-line') || '').toLowerCase();\n      if(sel==='all' || line===sel){\n        r.style.display = 'flex';\n      } else {\n        r.style.display = 'none';\n      }\n    });\n  } catch(e){ console.warn('tfl line filter failed', e); }\n  return '';\n}",
            Output(f"{self.component_id}-line-filter", "title"),  # dummy no-op output
            Input(f"{self.component_id}-line-filter", "value"),
            prevent_initial_call=False,
        )
