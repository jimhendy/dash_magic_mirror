import datetime
import os
from dataclasses import dataclass

from dash import Input, Output, dcc
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from components.base import BaseComponent
from components.google_calendar.callbacks import GoogleCalendarCallbacks
from components.google_calendar.layout import GoogleCalendarLayoutMixin
from utils.file_cache import cache_json


@dataclass
class CalendarConfig:
    calendar_ids: list[str]
    max_events: int = 10


class GoogleCalendar(BaseComponent, GoogleCalendarLayoutMixin):
    """Google Calendar component using the new modular architecture.

    This component inherits from BaseComponent and GoogleCalendarLayoutMixin to provide:
    - Summary view layout functionality
    - Integration with core modal system for detailed views
    - Clean separation of concerns
    - Well-documented and type-hinted code
    """

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    TOKEN_FILE = BaseComponent.credentials_dir() / ".google_calendar_token.json"
    CREDS_FILE = BaseComponent.credentials_dir() / "google_calendar_credentials.json"

    def __init__(
        self,
        calendar_config: CalendarConfig,
        *args,
        title: str = "Upcoming Events",
        **kwargs,
    ):
        """Initialize Google Calendar component.

        Args:
            calendar_config: Configuration object with calendar IDs and settings
            title: Display title for the component

        """
        super().__init__(name="google_calendar", *args, **kwargs)

        self.calendar_config = calendar_config
        self.title = title

        # Initialize callback manager
        self.callback_manager = GoogleCalendarCallbacks(self.component_id, self.fetch)
        self.title = title

        # Initialize callback manager
        self.callback_manager = GoogleCalendarCallbacks(self.component_id, self.fetch)

    def summary_layout(self):
        """Get the component layout using the layout mixin.

        Returns:
            Complete Dash layout with summary view and core modal integration

        """
        summary_layout = self.get_summary_layout()

        # Add the data fetch interval and store to the layout
        summary_layout.children.insert(
            0,
            dcc.Interval(
                id=f"{self.component_id}-interval-fetch",
                interval=60 * 5 * 1_000,  # 5 minutes
            ),
        )

        summary_layout.children.insert(
            1,
            dcc.Store(
                id=f"{self.component_id}-store",
                data=None,
            ),
        )

        return summary_layout

    @cache_json(valid_lifetime=datetime.timedelta(hours=1))
    def fetch(self) -> list[dict]:
        """Fetch events from Google Calendar API.

        Returns:
            List of event dictionaries from the calendar

        """
        creds = None
        if os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDS_FILE,
                    self.SCOPES,
                )
                creds = flow.run_local_server(port=0)
            with open(self.TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        try:
            service = build("calendar", "v3", credentials=creds)
            now = datetime.datetime.now(tz=datetime.UTC).isoformat()
            events = []
            for c_id in self.calendar_config.calendar_ids:
                events_result = (
                    service.events()
                    .list(
                        calendarId=c_id,
                        timeMin=now,
                        maxResults=self.calendar_config.max_events,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
                for event in events_result.get("items", []):
                    event["calendarId"] = c_id  # Tag event with its calendar
                    events.append(event)
            # Sort all events by start time
            events.sort(
                key=lambda e: e["start"].get("dateTime", e["start"].get("date", "")),
            )
            return events[: self.calendar_config.max_events]
        except HttpError as error:
            logger.error(f"Google Calendar API error: {error}")
            return []

    def add_callbacks(self, app):
        """Register all callbacks with the Dash app.

        Args:
            app: Dash application instance

        """

        # Register data fetch callback
        @app.callback(
            Output(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
        )
        def fetch_events(_):
            """Fetch calendar events on interval."""
            return self.fetch()

        # Register all other callbacks through the callback manager
        self.callback_manager.register_callbacks(app)
