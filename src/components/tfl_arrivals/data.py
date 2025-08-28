import datetime
import os
from typing import Any

import httpx
from loguru import logger

from utils.file_cache import cache_json

# TFL API endpoints
ARRIVALS_API_URL = "https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"
LINE_STATUS_API_URL = "https://api.tfl.gov.uk/Line/{line_ids}/Status"
STOPPOINT_DISRUPTION_API_URL = "https://api.tfl.gov.uk/StopPoint/{stop_ids}/Disruption"


@cache_json(valid_lifetime=datetime.timedelta(seconds=30))
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


def process_arrivals_data(arrivals: list[dict]) -> dict[str, Any]:
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

    # Process arrivals for display
    processed_arrivals = []
    for arrival in arrivals:
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
                    "destination": clean_station_name(
                        arrival.get("destinationName", ""),
                    ),
                    "platform": arrival.get("platformName", "Unknown"),
                    "line_name": arrival.get("lineName", ""),
                    "line_id": arrival.get("lineId", ""),
                    "direction": arrival.get("direction", ""),
                    "mode": arrival.get("modeName", ""),
                    "station_name": clean_station_name(arrival.get("stationName", "")),
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
