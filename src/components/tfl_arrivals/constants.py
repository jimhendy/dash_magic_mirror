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

# Canonical TFL line colours (by line id)
# Source: Transport for London brand guidelines (approximate hex values)
LINE_COLORS: dict[str, str] = {
    # London Underground
    "Bakerloo": "#B26300",
    "Central": "#DC241F",
    "Circle": "#FFC80A",
    "District": "#007D32",
    "Hammersmith & City": "#F589A6",
    "Jubilee": "#838D93",
    "Metropolitan": "#9B0058",
    "Northern": "#000000",
    "Piccadilly": "#0019A8",
    "Victoria": "#039BE5",
    "Waterloo & City": "#76D0BD",
    # Elizabeth line & DLR
    "Elizabeth line": "#60399E",
    "DLR": "#00AFAD",
    # London Overground – new named lines (2024)
    "Liberty": "#5D6061",
    "Lioness": "#FAA61A",
    "Mildmay": "#0077AD",
    "Suffragette": "#5BBD72",
    "Weaver": "#823A62",
    "Windrush": "#ED1B00",
    # Other TfL modes
    "London Overground (legacy mode colour)": "#FA7B05",
    "Tram": "#5FB526",
}

# Fallback colours
# TfL bus red; used for bus routes not in LINE_COLORS
BUS_FALLBACK_COLOR: str = "#EE3124"
# Generic non-bus (rail/tube) fallback; aligned with app's blue accent
RAIL_FALLBACK_COLOR: str = "#4A90E2"
