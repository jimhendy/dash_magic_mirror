import asyncio

from loguru import logger

from components.base import DataDrivenComponent
from utils.data_repository import ComponentPayload
from utils.styles import COLORS

from .data import (
    fetch_arrivals_for_stop,
    fetch_line_status,
    fetch_stoppoint_disruptions,
    process_arrivals_data,
    process_line_status_data,
    process_stoppoint_disruptions,
)
from .full_screen import render_tfl_fullscreen
from .summary import render_tfl_badge, render_tfl_summary


class TFLArrivals(DataDrivenComponent):
    """TFL Arrivals component for the Magic Mirror application.

    Every configured stop is fetched once per refresh and processed two
    ways from that single fetch: a direction-filtered, merged-across-stops
    view for the summary timeline, and a per-stop unfiltered view for the
    full-screen list (which has its own line filter for exploring
    everything). Previously these were two separate fetch paths and the
    "primary" stop was actually fetched twice per cycle - fetching once
    and reusing it for both views is both simpler and less wasteful.
    """

    title = "Transport"
    icon = "mdi:train-car"
    accent = COLORS["urgent"]
    refresh_seconds = 30
    jitter_seconds = 10
    placeholder_error = "Transport data unavailable"
    placeholder_loading = "Loading departures…"

    def __init__(
        self,
        all_stop_ids: list[str],
        summary_ignore_destination: str = "",
        line_status_ids: list[str] | None = None,
        **kwargs,
    ):
        self.all_stop_ids = all_stop_ids
        self.summary_ignore_destination = summary_ignore_destination
        self._line_status_ids = list(line_status_ids or [])
        if not self.all_stop_ids:
            logger.warning("No TFL stop ids configured for TFLArrivals")
        super().__init__(name="tfl_arrivals", **kwargs)

    async def _build_payload(self) -> ComponentPayload | None:
        return await asyncio.to_thread(self._compute_payload_sync)

    def _compute_payload_sync(self) -> ComponentPayload | None:
        if not self.all_stop_ids:
            message = self._build_placeholder("Transport stops not configured")
            return ComponentPayload(summary=message, detail=message)

        try:
            timeline_arrivals, arrivals_by_stop, line_status, stop_disruptions = (
                self._get_arrivals_data()
            )
            summary = render_tfl_summary(
                timeline_arrivals,
                priority_line_ids=self._line_status_ids,
                line_status=line_status,
            )
            detail = render_tfl_fullscreen(
                arrivals_by_stop, line_status, stop_disruptions
            )
            badge = render_tfl_badge(
                line_status, stop_disruptions, self._line_status_ids
            )
        except Exception:  # noqa: BLE001
            logger.exception("Error building TFL payload")
            return None

        stops = [
            s.get("station_name")
            for s in arrivals_by_stop.values()
            if s.get("station_name")
        ]
        return ComponentPayload(
            summary=summary,
            detail=detail,
            subtitle=" · ".join(stops) or "Live departures",
            badge=badge,
            raw={
                "timeline": timeline_arrivals,
                "full": arrivals_by_stop,
                "status": line_status,
                "disruptions": stop_disruptions,
            },
        )

    def _get_arrivals_data(self):
        raw_by_stop = {
            stop_id: fetch_arrivals_for_stop(stop_id) for stop_id in self.all_stop_ids
        }

        # Summary timeline: direction-filtered (via summary_ignore_destination)
        # and merged across every configured stop, sorted by arrival time.
        timeline_arrivals: list[dict] = []
        all_line_ids = set(self._line_status_ids)
        for raw in raw_by_stop.values():
            processed = process_arrivals_data(
                raw,
                self.summary_ignore_destination,
                is_summary=True,
            )
            timeline_arrivals.extend(processed["arrivals"])
            if not self._line_status_ids:
                all_line_ids.update(processed["line_ids"])
        timeline_arrivals.sort(key=lambda a: a["minutes"])

        # Full-screen: unfiltered (every direction), kept per-stop.
        arrivals_by_stop: dict[str, dict] = {}
        for stop_id, raw in raw_by_stop.items():
            processed = process_arrivals_data(
                raw,
                self.summary_ignore_destination,
                is_summary=False,
            )
            line_ids = list(self._line_status_ids) or processed["line_ids"]
            processed["line_ids"] = line_ids
            arrivals_by_stop[stop_id] = processed
            all_line_ids.update(line_ids)

        line_status_raw = fetch_line_status(list(all_line_ids)) if all_line_ids else []
        line_status = process_line_status_data(line_status_raw)
        stop_disruptions_raw = fetch_stoppoint_disruptions(self.all_stop_ids)
        stop_disruptions = process_stoppoint_disruptions(stop_disruptions_raw)
        return timeline_arrivals, arrivals_by_stop, line_status, stop_disruptions
