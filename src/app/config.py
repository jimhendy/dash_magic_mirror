import os
from pathlib import Path

from dotenv import load_dotenv

from components.clock import Clock
from components.google_calendar import CalendarConfig, GoogleCalendar
from components.news_compliments import NewsComplimentsFeed
from components.sports import Sports
from components.tfl_arrivals import TFL
from components.weather import Weather

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
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
    # Google Calendar
    GoogleCalendar(
        calendar_config=CalendarConfig(
            calendar_ids=[
                os.environ[calendar_id]
                for calendar_id in os.environ
                if calendar_id.startswith("GOOGLE_CALENDAR_ID_")
            ],
        ),
        maxHeight="20%",
    ),
    # TFL Transport Arrivals
    TFL(
        stops=[
            os.environ[stop_id]
            for stop_id in os.environ
            if stop_id.startswith("TFL_STOP_ID_")
        ],
        maxHeight="20%",
        separator=True,
    ),
    # Sports Fixtures
    Sports(
        separator=True,
        maxHeight="25%",
    ),
    # News & Compliments Feed at bottom
    NewsComplimentsFeed(
        marginTop="auto",
        separator=True,
    ),
    # Total: 105% (may need adjustment)
]
