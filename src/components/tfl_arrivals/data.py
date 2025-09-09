import datetime
import os
from typing import Any

import httpx
from dash_iconify import DashIconify
from loguru import logger

from utils.file_cache import cache_json

# TFL API endpoints
ARRIVALS_API_URL = "https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"
LINE_STATUS_API_URL = "https://api.tfl.gov.uk/Line/{line_ids}/Status"
STOPPOINT_DISRUPTION_API_URL = "https://api.tfl.gov.uk/StopPoint/{stop_ids}/Disruption"
TIMETABLE_API_URL = (
    "https://api.tfl.gov.uk/Line/{line_id}/Timetable/{from_stop_id}/to/{to_stop_id}"
)


# Station IDs from environment variables
def get_transfer_station_id() -> str:
    """Get the transfer station ID for checking connections."""
    return os.environ.get("TFL_TRANSFER_STATION_ID", "")


@cache_json(valid_lifetime=datetime.timedelta(minutes=5))
def fetch_timetable(line_id: str, from_stop_id: str, to_stop_id: str) -> dict:
    """Fetch timetable data between two stops to check calling patterns."""
    try:
        response = httpx.get(
            TIMETABLE_API_URL.format(
                line_id=line_id,
                from_stop_id=from_stop_id,
                to_stop_id=to_stop_id,
            ),
            timeout=10,
        )
        if response.is_success:
            return response.json()
        logger.error(
            f"Failed to fetch timetable for {line_id} from {from_stop_id} to {to_stop_id}: {response.status_code}",
        )
        return {}
    except httpx.RequestError as e:
        logger.error(
            f"Error fetching timetable for {line_id} from {from_stop_id} to {to_stop_id}: {e}",
        )
        return {}


@cache_json(valid_lifetime=datetime.timedelta(seconds=60))
def fetch_transfer_station_arrivals() -> list[dict]:
    """Fetch arrivals at transfer station."""
    transfer_station_id = get_transfer_station_id()
    if not transfer_station_id:
        return []
    return fetch_arrivals_for_stop(transfer_station_id)


# --- Transfer station matching improvements ----------------------------------------------------

def _normalise_destination(name: str) -> str:
    if not name:
        return ""
    return clean_station_name(name).strip().lower()


def build_transfer_station_index(transfer_station_arrivals: list[dict]) -> dict:
    """Build lookup structures for efficient transfer station matching.

    Returns dict with:
      by_vehicle: vehicleId -> list[arrivals]
      by_line_dest: (lineId, destinationKey) -> list[arrivals]
    destinationKey prefers destinationNaptanId; falls back to normalised destination name.
    """
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
) -> bool:
    """Determine if the given arrival will also call at the configured transfer station *after* this stop.

    Additional rule vs previous implementation:
      Only return True if the matched prediction at the transfer station has an expectedArrival
      strictly later than the expectedArrival at the current stop (i.e. the transfer station is
      still ahead). If the transfer station time is earlier or equal, the train has already
      passed it, so we suppress the indicator.
    """
    if not transfer_station_arrivals:
        return False

    transfer_station_id = get_transfer_station_id()

    # If this prediction is already for the transfer station, no indicator needed.
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

    # Minimum forward delta (seconds) to regard transfer station as ahead (guard against clock jitter)
    FORWARD_DELTA_SECONDS = 15

    for ts_arr in transfer_station_arrivals:
        # Lines must match for a valid comparison.
        if ts_arr.get("lineId") != line_id:
            continue

        ts_vehicle_id = ts_arr.get("vehicleId") or ""
        ts_dest_id = ts_arr.get("destinationNaptanId") or ""
        ts_dest_name_norm = normalize_destination_name(ts_arr.get("destinationName", ""))

        matched = False

        # 1 & 2: vehicleId led matching.
        if vehicle_id and ts_vehicle_id and vehicle_id == ts_vehicle_id:
            if dest_id and ts_dest_id:
                matched = dest_id == ts_dest_id
            elif dest_name_norm and ts_dest_name_norm:
                matched = dest_name_norm == ts_dest_name_norm
            else:
                matched = False
        # 3: Fallback (only when vehicleId missing on either side): match by line + destination.
        elif (not vehicle_id or not ts_vehicle_id):
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

        # Ordering check – ensure transfer station call is after current stop.
        ts_expected_dt = _parse_expected(ts_arr.get("expectedArrival"))
        if not ts_expected_dt:
            continue  # cannot confirm ordering, be conservative (no indicator)

        delta = (ts_expected_dt - arrival_expected_dt).total_seconds()
        if delta > FORWARD_DELTA_SECONDS:
            return True  # Transfer station still ahead
        else:
            # Transfer station prediction is earlier/same -> it is behind or at this stop already
            continue

    return False


def normalize_destination_name(name: str) -> str:
    """Normalize destination/station names for comparison."""
    if not name:
        return ""
    return clean_station_name(name).strip().lower()


def get_transfer_station_indicator(
    arrival: dict,
    transfer_station_arrivals: list[dict],
    is_summary: bool = False,
) -> str:
    """Get indicator symbol for trains that stop at transfer station."""
    if check_stops_at_transfer_station(arrival, transfer_station_arrivals):
        if is_summary:
            return DashIconify(
                icon="mdi:alpha-b-circle-outline",
                color="green",
                width=30,
                height=30,
            )
        return "✓"  # Tick for full screen
    return ""


@cache_json(valid_lifetime=datetime.timedelta(seconds=60))
def fetch_arrivals_for_stop(stop_id: str) -> list[dict]:
    """Fetch arrivals for a single stop."""
    try:
        response = httpx.get(ARRIVALS_API_URL.format(stop_id=stop_id), timeout=10)
        if response.is_success:
            arrivals = response.json()
            if arrivals:
                # Add stop info to each arrival
                for arrival in arrivals:
                    arrival["stopId"] = stop_id
                # Sort by expected arrival time
                arrivals.sort(key=lambda x: x.get("expectedArrival", ""))
                return arrivals
            return []
        logger.error(
            f"Failed to fetch arrivals for stop {stop_id}: {response.status_code}",
        )
        return []
    except httpx.RequestError as e:
        logger.error(f"Error fetching arrivals for stop {stop_id}: {e}")
        return []


@cache_json(valid_lifetime=datetime.timedelta(minutes=2))
def fetch_line_status(line_ids: list[str]) -> list[dict]:
    """Fetch line status for given line IDs."""
    if not line_ids:
        return []

    line_ids_str = ",".join(line_ids)
    try:
        response = httpx.get(
            LINE_STATUS_API_URL.format(line_ids=line_ids_str),
            timeout=10,
        )
        if response.is_success:
            return response.json()
        logger.error(
            f"Failed to fetch line status for lines {line_ids_str}: {response.status_code}",
        )
        return []
    except httpx.RequestError as e:
        logger.error(f"Error fetching line status for lines {line_ids_str}: {e}")
        return []


@cache_json(valid_lifetime=datetime.timedelta(minutes=2))
def fetch_stoppoint_disruptions(stop_ids: list[str]) -> list[dict]:
    """Fetch stoppoint disruptions for given stop IDs."""
    if not stop_ids:
        return []

    stop_ids_str = ",".join(stop_ids)
    try:
        response = httpx.get(
            STOPPOINT_DISRUPTION_API_URL.format(stop_ids=stop_ids_str),
            timeout=10,
        )
        if response.is_success:
            return response.json()
        logger.error(
            f"Failed to fetch stoppoint disruptions for stops {stop_ids_str}: {response.status_code}",
        )
        return []
    except httpx.RequestError as e:
        logger.error(
            f"Error fetching stoppoint disruptions for stops {stop_ids_str}: {e}",
        )
        return []


def get_all_stop_ids() -> list[str]:
    """Get all TFL stop IDs from environment variables."""
    return [
        os.environ[stop_id]
        for stop_id in os.environ
        if stop_id.startswith("TFL_STOP_ID_")
    ]


def get_primary_stop_id() -> str:
    """Get the primary TFL stop ID (TFL_STOP_ID_1) for summary view."""
    return os.environ.get("TFL_STOP_ID_1", "")


def process_arrivals_data(
    arrivals: list[dict],
    is_summary: bool = False,
) -> dict[str, Any]:
    """Process arrivals data for rendering."""
    if not arrivals:
        return {
            "arrivals": [],
            "line_ids": [],
            "station_name": "",
        }

    # Extract unique line IDs for status checking
    line_ids = list(
        set(arrival.get("lineId", "") for arrival in arrivals if arrival.get("lineId")),
    )

    # Get station name from first arrival
    station_name = arrivals[0].get("stationName", "Unknown Station")

    # Fetch transfer station arrivals once
    transfer_station_arrivals = fetch_transfer_station_arrivals()

    # Get ignore destination for summary filtering
    ignore_destination = os.environ.get("TFL_SUMMARY_IGNORE_DESTINATION", "")

    # Process arrivals for display
    processed_arrivals = []
    for arrival in arrivals:
        # Filter out ignored destinations in summary view
        destination = arrival.get("destinationName", "")
        if (
            is_summary
            and ignore_destination
            and ignore_destination.lower() in destination.lower()
        ):
            continue

        # Calculate time until arrival
        arrival_time_str = arrival.get("expectedArrival", "")
        if arrival_time_str:
            try:
                arrival_time = datetime.datetime.fromisoformat(
                    arrival_time_str.replace("Z", "+00:00"),
                )
                now = datetime.datetime.now(datetime.UTC)
                time_diff = (arrival_time - now).total_seconds()
                minutes = max(0, int(time_diff // 60))

                # Skip arrivals that have already passed or are too far away
                if minutes < 0 or minutes > 60:
                    continue

                processed_arrival = {
                    "id": arrival.get("id", ""),
                    "minutes": minutes,
                    "arrival_time": arrival_time,  # Store the actual arrival time
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
