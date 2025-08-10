import os
from pathlib import Path

from dotenv import load_dotenv

from components.clock import Clock
from components.compliments_jokes import ComplimentsJokes
from components.google_calendar import CalendarConfig, GoogleCalendar
from components.news import NewsFeed
from components.tfl_arrivals import TFL

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


# Create component instances with configuration from environment
COMPONENTS = [
    Clock(
        top="1%",
        # Ensure horizontal centering
        h_center=True,
    ),
    GoogleCalendar(
        calendar_config=CalendarConfig(
            calendar_ids=[
                os.environ[calendar_id]
                for calendar_id in os.environ
                if calendar_id.startswith("GOOGLE_CALENDAR_ID_")
            ],
        ),
        top="1%",
        right="1%",
        maxWidth="40%",
        maxHeight="40%",
    ),
    TFL(
        stops=[
            os.environ[stop_id]
            for stop_id in os.environ
            if stop_id.startswith("TFL_LEFT_STOP_ID_")
        ],
        left="1%",
        top="65%",
        width="40%",
        maxHeight="30%",
    ),
    TFL(
        stops=[
            os.environ[stop_id]
            for stop_id in os.environ
            if stop_id.startswith("TFL_RIGHT_STOP_ID_")
        ],
        right="1%",
        top="65%",
        width="40%",
        maxHeight="30%",
    ),
    ComplimentsJokes(
        v_center=True,
        h_center=True,
        maxWidth="60%",
        maxHeight="20%",
    ),
    NewsFeed(
        bottom="1%",
        h_center=True,
        maxWidth="80%",
        maxHeight="20%",
    ),
]
