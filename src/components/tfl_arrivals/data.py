import datetime
import json
import time
from typing import Any

import httpx
from dash_iconify import DashIconify
from loguru import logger

from utils.file_cache import cache_json

from .constants import (
    ARRIVALS_API_URL,
    FORWARD_DELTA_SECONDS,
    LINE_STATUS_API_URL,
    STOPPOINT_DISRUPTION_API_URL,
    TIMETABLE_API_URL,
)

# --- Robust HTTP helpers ----------------------------------------------------------------------

_MAX_RESPONSE_BYTES = 1_000_000  # 1MB safety cap


def _empty_for(expected_type: str):  # helper to supply empty placeholder
    return [] if expected_type == "list" else {}


def _http_get_json(
    url: str,
    *,
    timeout: float = 10.0,
    expected_type: str = "list",  # 'list' or 'dict'
    max_retries: int = 2,
    retry_backoff_base: float = 0.25,
) -> Any:
    """HTTP GET + robust JSON parsing with limited retries.

    Handles intermittent TFL API issues where multiple JSON payloads or partial content
    cause json.JSONDecodeError (e.g. 'Extra data: line ...'). Attempts a truncation based
    fallback for common cases where trailing noise was appended.
    """
    attempt = 0
    while attempt <= max_retries:
        try:
            response = httpx.get(url, timeout=timeout)
        except httpx.RequestError as e:
            if attempt < max_retries:
                sleep_for = retry_backoff_base * (2**attempt)
                logger.warning(
                    f"Request error {e} fetching {url}. Retry {attempt + 1}/{max_retries} in {sleep_for:.2f}s",
                )
                time.sleep(sleep_for)
                attempt += 1
                continue
            logger.error(f"Failed to fetch {url}: {e}")
            return _empty_for(expected_type)

        status = response.status_code
        if status >= 500 and attempt < max_retries:
            sleep_for = retry_backoff_base * (2**attempt)
            logger.warning(
                f"Server error {status} fetching {url}. Retry {attempt + 1}/{max_retries} in {sleep_for:.2f}s",
            )
            time.sleep(sleep_for)
            attempt += 1
            continue
        if not response.is_success:
            logger.error(f"Non-success status {status} fetching {url}")
            return _empty_for(expected_type)

        # Size guard
        if len(response.content) > _MAX_RESPONSE_BYTES:
            logger.error(
                f"Aborting parse for {url} - response too large ({len(response.content)} bytes)",
            )
            return _empty_for(expected_type)

        # Fast path
        try:
            parsed = response.json()
            return (
                parsed
                if isinstance(parsed, (list, dict))
                else _empty_for(expected_type)
            )
        except json.JSONDecodeError as e:
            raw_text = response.text.strip()
            logger.warning(
                f"JSON decode error for {url}: {e}. Attempting fallback parse (attempt {attempt + 1}/{max_retries + 1})",
            )
            fallback = None
            # Truncation-based salvage: find last closing bracket/brace matching first char
            if raw_text.startswith("["):
                last = raw_text.rfind("]")
                if last != -1:
                    candidate = raw_text[: last + 1]
                    try:
                        fallback = json.loads(candidate)
                    except Exception:  # noqa: BLE001
                        fallback = None
            elif raw_text.startswith("{"):
                last = raw_text.rfind("}")
                if last != -1:
                    candidate = raw_text[: last + 1]
                    try:
                        fallback = json.loads(candidate)
                    except Exception:  # noqa: BLE001
                        fallback = None
            if fallback is not None:
                logger.warning(
                    f"Recovered JSON via truncation for {url} (len={len(raw_text)})",
                )
                return fallback

            # Final retry decision
            if attempt < max_retries:
                sleep_for = retry_backoff_base * (2**attempt)
                snippet_head = raw_text[:200].replace("\n", " ")
                snippet_tail = (
                    raw_text[-120:].replace("\n", " ") if len(raw_text) > 320 else ""
                )
                logger.debug(
                    f"Retrying after decode failure. Head: {snippet_head} ... Tail: {snippet_tail}",
                )
                time.sleep(sleep_for)
                attempt += 1
                continue
            snippet = raw_text[:300].replace("\n", " ")
            logger.error(
                f"Failed to parse JSON for {url} after {attempt + 1} attempts. Snippet: {snippet}",
            )
            return _empty_for(expected_type)
        except Exception as e:  # noqa: BLE001 - unexpected parsing path
            logger.error(f"Unexpected error parsing JSON for {url}: {e}")
            return _empty_for(expected_type)

    return _empty_for(expected_type)


# --- Data fetch functions (parameterised, no env reads) ----------------------------------------


def fetch_timetable(line_id: str, from_stop_id: str, to_stop_id: str) -> dict:
    url = TIMETABLE_API_URL.format(
        line_id=line_id,
        from_stop_id=from_stop_id,
        to_stop_id=to_stop_id,
    )
    data = _http_get_json(url, expected_type="dict")
    return data if isinstance(data, dict) else {}


@cache_json(valid_lifetime=datetime.timedelta(seconds=60))
def fetch_arrivals_for_stop(stop_id: str) -> list[dict]:
    url = ARRIVALS_API_URL.format(stop_id=stop_id)
    data = _http_get_json(url, expected_type="list")
    if not isinstance(data, list):
        return []
    arrivals: list[dict] = data
    if arrivals:
        for arrival in arrivals:
            arrival["stopId"] = stop_id
        try:
            arrivals.sort(key=lambda x: x.get("expectedArrival", ""))
        except Exception:  # noqa: BLE001
            pass
    return arrivals


@cache_json(valid_lifetime=datetime.timedelta(seconds=60))
def fetch_transfer_station_arrivals(transfer_station_id: str) -> list[dict]:
    if not transfer_station_id:
        return []
    return fetch_arrivals_for_stop(transfer_station_id)


@cache_json(valid_lifetime=datetime.timedelta(minutes=2))
def fetch_line_status(line_ids: list[str]) -> list[dict]:
    if not line_ids:
        return []
    line_ids_str = ",".join(line_ids)
    url = LINE_STATUS_API_URL.format(line_ids=line_ids_str)
    data = _http_get_json(url, expected_type="list")
    return data if isinstance(data, list) else []


@cache_json(valid_lifetime=datetime.timedelta(minutes=2))
def fetch_stoppoint_disruptions(stop_ids: list[str]) -> list[dict]:
    if not stop_ids:
        return []
    stop_ids_str = ",".join(stop_ids)
    url = STOPPOINT_DISRUPTION_API_URL.format(stop_ids=stop_ids_str)
    data = _http_get_json(url, expected_type="list")
    return data if isinstance(data, list) else []


# --- Transfer station matching ---------------------------------------------------------------


def _normalise_destination(name: str) -> str:
    if not name:
        return ""
    return clean_station_name(name).strip().lower()


def build_transfer_station_index(transfer_station_arrivals: list[dict]) -> dict:
    by_vehicle: dict[str, list] = {}
    by_line_dest: dict[tuple[str, str], list] = {}
    for arr in transfer_station_arrivals:
        vehicle_id = arr.get("vehicleId") or ""
        line_id = arr.get("lineId") or ""
        dest_id = arr.get("destinationNaptanId") or ""
        dest_name = arr.get("destinationName", "")
        destination_key = dest_id if dest_id else _normalise_destination(dest_name)
        if vehicle_id:
            by_vehicle.setdefault(vehicle_id, []).append(arr)
        if line_id and destination_key:
            by_line_dest.setdefault((line_id, destination_key), []).append(arr)
    return {"by_vehicle": by_vehicle, "by_line_dest": by_line_dest}


def _parse_expected(dt_str: str) -> datetime.datetime | None:
    if not dt_str:
        return None
    try:
        return datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def check_stops_at_transfer_station(
    arrival: dict,
    transfer_station_arrivals: list[dict],
    transfer_station_id: str,
) -> bool:
    if not transfer_station_arrivals or not transfer_station_id:
        return False
    if arrival.get("naptanId") == transfer_station_id:
        return False
    vehicle_id = arrival.get("vehicleId") or ""
    line_id = arrival.get("lineId") or ""
    dest_id = arrival.get("destinationNaptanId") or ""
    dest_name_norm = normalize_destination_name(arrival.get("destinationName", ""))
    if not line_id:
        return False
    arrival_expected_dt = _parse_expected(arrival.get("expectedArrival"))
    if not arrival_expected_dt:
        return False
    for ts_arr in transfer_station_arrivals:
        if ts_arr.get("lineId") != line_id:
            continue
        ts_vehicle_id = ts_arr.get("vehicleId") or ""
        ts_dest_id = ts_arr.get("destinationNaptanId") or ""
        ts_dest_name_norm = normalize_destination_name(
            ts_arr.get("destinationName", ""),
        )
        matched = False
        if vehicle_id and ts_vehicle_id and vehicle_id == ts_vehicle_id:
            if dest_id and ts_dest_id:
                matched = dest_id == ts_dest_id
            elif dest_name_norm and ts_dest_name_norm:
                matched = dest_name_norm == ts_dest_name_norm
        elif not vehicle_id or not ts_vehicle_id:
            if dest_id and ts_dest_id:
                matched = dest_id == ts_dest_id
            elif (
                (not dest_id or not ts_dest_id)
                and dest_name_norm
                and ts_dest_name_norm
                and dest_name_norm == ts_dest_name_norm
            ):
                matched = True
        if not matched:
            continue
        ts_expected_dt = _parse_expected(ts_arr.get("expectedArrival"))
        if not ts_expected_dt:
            continue
        delta = (ts_expected_dt - arrival_expected_dt).total_seconds()
        if delta > FORWARD_DELTA_SECONDS:
            return True
    return False


def normalize_destination_name(name: str) -> str:
    if not name:
        return ""
    return clean_station_name(name).strip().lower()


def get_transfer_station_indicator(
    arrival: dict,
    transfer_station_arrivals: list[dict],
    transfer_station_id: str,
    is_summary: bool = False,
) -> str:
    if check_stops_at_transfer_station(
        arrival,
        transfer_station_arrivals,
        transfer_station_id,
    ):
        if is_summary:
            return DashIconify(
                icon="mdi:alpha-b-circle-outline",
                color="green",
                width=30,
                height=30,
            )
        return "✓"
    return ""


# --- Processing ------------------------------------------------------------------------------


def process_arrivals_data(
    arrivals: list[dict],
    transfer_station_arrivals: list[dict],
    transfer_station_id: str,
    ignore_destination: str,
    is_summary: bool = False,
) -> dict[str, Any]:
    if not arrivals:
        return {
            "arrivals": [],
            "line_ids": [],
            "station_name": "",
        }
    line_ids = list(
        set(arrival.get("lineId", "") for arrival in arrivals if arrival.get("lineId")),
    )
    station_name = arrivals[0].get("stationName", "Unknown Station")
    processed_arrivals = []
    for arrival in arrivals:
        destination = arrival.get("destinationName", "")
        if (
            is_summary
            and ignore_destination
            and ignore_destination.lower() in destination.lower()
        ):
            continue
        arrival_time_str = arrival.get("expectedArrival", "")
        if arrival_time_str:
            try:
                arrival_time = datetime.datetime.fromisoformat(
                    arrival_time_str.replace("Z", "+00:00"),
                )
                now = datetime.datetime.now(datetime.UTC)
                time_diff = (arrival_time - now).total_seconds()
                minutes = max(0, int(time_diff // 60))
                if minutes < 0 or minutes > 60:
                    continue
                processed_arrival = {
                    "id": arrival.get("id", ""),
                    "minutes": minutes,
                    "arrival_time": arrival_time,
                    "destination": clean_station_name(destination),
                    "platform": arrival.get("platformName", "Unknown"),
                    "line_name": arrival.get("lineName", ""),
                    "line_id": arrival.get("lineId", ""),
                    "direction": arrival.get("direction", ""),
                    "mode": arrival.get("modeName", ""),
                    "station_name": clean_station_name(arrival.get("stationName", "")),
                    "transfer_station_indicator": get_transfer_station_indicator(
                        arrival,
                        transfer_station_arrivals,
                        transfer_station_id,
                        is_summary,
                    ),
                }
                processed_arrivals.append(processed_arrival)
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing arrival time: {e}")
                continue
    return {
        "arrivals": processed_arrivals,
        "line_ids": line_ids,
        "station_name": clean_station_name(station_name),
    }


def process_line_status_data(line_status_data: list[dict]) -> dict[str, dict]:
    """Process line status data into a dictionary keyed by line ID."""
    status_dict = {}

    for line in line_status_data:
        line_id = line.get("id", "")
        line_name = line.get("name", "")
        line_statuses = line.get("lineStatuses", [])

        if line_statuses:
            # Get the first/primary status
            primary_status = line_statuses[0]
            status_severity = primary_status.get("statusSeverity", 10)
            status_description = primary_status.get(
                "statusSeverityDescription",
                "Unknown",
            )
            reason = primary_status.get("reason", "")

            # Determine status color based on severity
            # TFL severity: 10=Good Service, lower numbers indicate problems
            if status_severity == 10:
                status_color = "green"
                status_text = "Good Service"
            elif status_severity >= 6:
                status_color = "yellow"
                status_text = status_description
            else:
                status_color = "red"
                status_text = status_description

            status_dict[line_id] = {
                "line_name": line_name,
                "status_text": status_text,
                "status_color": status_color,
                "severity": status_severity,
                "reason": reason,
            }

    return status_dict


def process_stoppoint_disruptions(disruption_data: list[dict]) -> dict[str, list]:
    """Process stoppoint disruption data into a dictionary keyed by stop ID."""
    disruptions_dict = {}

    for disruption in disruption_data:
        stop_points = disruption.get("affectedStops", [])
        description = disruption.get("description", "")
        category = disruption.get("category", "")

        for stop in stop_points:
            stop_id = stop.get("id", "")
            if stop_id:
                if stop_id not in disruptions_dict:
                    disruptions_dict[stop_id] = []
                disruptions_dict[stop_id].append(
                    {
                        "description": description,
                        "category": category,
                    },
                )

    return disruptions_dict


# --- Misc utilities -------------------------------------------------------------------------


def clean_station_name(station_name: str) -> str:
    """Clean station name by removing common suffixes."""
    if not station_name:
        return station_name

    return (
        station_name.replace(" Rail Station", "")
        .replace(" Underground Station", "")
        .replace(" Station", "")
    )


def get_time_color_and_weight(minutes: int) -> tuple[str, str]:
    """Get color and font weight for time display based on urgency."""
    if minutes < 2:
        return "#ff6b6b", "bold"  # Red for imminent
    if minutes < 5:
        return "#ffd93d", "500"  # Yellow for soon
    return "#ffffff", "400"  # White for normal
