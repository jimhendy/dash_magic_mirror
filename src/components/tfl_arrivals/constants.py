"""Constants for the TFL Arrivals component."""

# API Endpoints
ARRIVALS_API_URL: str = "https://api.tfl.gov.uk/StopPoint/{stop_id}/Arrivals"
LINE_STATUS_API_URL: str = "https://api.tfl.gov.uk/Line/{line_ids}/Status"
STOPPOINT_DISRUPTION_API_URL: str = (
    "https://api.tfl.gov.uk/StopPoint/{stop_ids}/Disruption"
)
TIMETABLE_API_URL: str = (
    "https://api.tfl.gov.uk/Line/{line_id}/Timetable/{from_stop_id}/to/{to_stop_id}"
)

# Matching / timing
FORWARD_DELTA_SECONDS: int = (
    15  # Minimum forward delta to regard transfer station as ahead
)
