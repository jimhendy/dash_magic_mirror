import os
from pathlib import Path

from dotenv import load_dotenv

from components.clock import Clock
from components.google_calendar import GoogleCalendar
from components.sports import Sports
from components.tfl_arrivals import TFLArrivals
from components.weather import Weather

# Load environment variables from .env file
env_path = Path(__file__).parents[2] / ".env"
load_dotenv(env_path)


# Create component instances with configuration from environment
# Single column layout with percentage-based heights (total should not exceed 100%)
COMPONENTS = [
    # Clock at the top - 15%
    Clock(),
    # Weather component
    Weather(
        postcode=os.environ.get("WEATHER_POSTCODE", "SW1A 1AA"),
        api_key=os.environ.get("WEATHER_API_KEY", ""),
    ),
    GoogleCalendar(
        calendar_ids=[
            os.environ[calendar_id]
            for calendar_id in os.environ
            if calendar_id.startswith("GOOGLE_CALENDAR_ID_")
        ],
    ),
    # TFL Transport Arrivals
    TFLArrivals(),
    # Sports Fixtures
    Sports(),
    # # News & Compliments Feed at bottom
    # NewsComplimentsFeed(
    #     marginTop="auto",
    #     separator=True,
    # ),
    # # Total: 105% (may need adjustment)
]
