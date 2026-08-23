import asyncio

from dash import Dash, Input, Output, html
from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload

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


class TFLArrivals(DataDrivenComponent):
    """TFL Arrivals component for the Magic Mirror application.

    Now fully parameterised; no direct environment reads in data layer.
    """

    refresh_seconds = 30
    jitter_seconds = 10
    placeholder_error = "Transport data unavailable"
    placeholder_loading = "Loading transport data..."

    def __init__(
        self,
        primary_stop_id: str,
        all_stop_ids: list[str],
        transfer_station_id: str = "",
        summary_ignore_destination: str = "",
        line_status_ids: list[str] | None = None,
        **kwargs,
    ):
        self.primary_stop_id = primary_stop_id
        self.all_stop_ids = all_stop_ids
        self.transfer_station_id = transfer_station_id
        self.summary_ignore_destination = summary_ignore_destination
        self._line_status_ids = list(line_status_ids or [])
        if not self.primary_stop_id:
            logger.warning("Primary stop id not provided for TFLArrivals")
        super().__init__(name="tfl_arrivals", **kwargs)

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
                summary=self._build_placeholder(self.placeholder_error),
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
        line_ids = list(self._line_status_ids) or arrivals_data.get("line_ids", [])

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
            line_ids = list(self._line_status_ids) or arrivals_data.get("line_ids", [])
            arrivals_data["line_ids"] = line_ids

            all_arrivals_data[stop_id] = arrivals_data
            all_line_ids.update(line_ids)
        line_status_raw = fetch_line_status(list(all_line_ids)) if all_line_ids else []
        line_status = process_line_status_data(line_status_raw)
        stop_disruptions_raw = fetch_stoppoint_disruptions(self.all_stop_ids)
        stop_disruptions = process_stoppoint_disruptions(stop_disruptions_raw)
        return all_arrivals_data, line_status, stop_disruptions

    def _add_callbacks(self, app: Dash) -> None:
        super()._add_callbacks(app)

        # Client-side filtering of arrivals rows by selected line
        app.clientside_callback(
            "function(value){\n  try {\n    const wrapper = document.getElementById('"
            f"{self.component_id}-arrivals-wrapper"
            "');\n    if(!wrapper){return window.dash_clientside.no_update;}\n    const rows = wrapper.querySelectorAll('[data-line]');\n    if(!rows.length){return window.dash_clientside.no_update;}\n    const sel = (value || 'all').toLowerCase();\n    rows.forEach(r=>{\n      const line = (r.getAttribute('data-line') || '').toLowerCase();\n      if(sel==='all' || line===sel){\n        r.style.display = 'flex';\n      } else {\n        r.style.display = 'none';\n      }\n    });\n  } catch(e){ console.warn('tfl line filter failed', e); }\n  return '';\n}",
            Output(f"{self.component_id}-line-filter", "title"),  # dummy no-op output
            Input(f"{self.component_id}-line-filter", "value"),
            prevent_initial_call=False,
        )
