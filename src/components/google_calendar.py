import datetime
import os
from dataclasses import dataclass

import dash_mantine_components as dmc
from dash import Input, Output, dcc, html
from dash_iconify import DashIconify
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from components.base import BaseComponent
from utils.file_cache import cache_json
from utils.styles import COLORS


@dataclass
class CalendarConfig:
    calendar_ids: list[str]
    max_events: int = 10


def datetime_from_str(datetime_str: str, *, is_all_day: bool) -> datetime.datetime:
    """Convert ISO datetime string to datetime object."""
    if is_all_day:
        return datetime.datetime.fromisoformat(datetime_str + "T00:00:00")
    return datetime.datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))


def format_datetime(date_obj: datetime.datetime, *, is_all_day: bool) -> str:
    """Format date/time for display."""
    if is_all_day:
        # For all-day events, show only the date
        return date_obj.strftime("%a %d %b")
    return date_obj.strftime("%a %d %b %H:%M")


def is_today(date_obj: datetime.datetime) -> bool:
    """Check if event is today."""
    return date_obj.date() <= datetime.date.today()


def is_tomorrow(date_obj: datetime.datetime) -> bool:
    """Check if event is tomorrow."""
    return date_obj.date() == (datetime.date.today() + datetime.timedelta(days=1))


def is_multi_day(start: datetime.datetime, end: datetime.datetime | None) -> bool:
    """Check if event spans multiple days."""
    if not end:
        return False
    return start.date() != end.date()


def get_corrected_end_date(
    end: datetime.datetime | None,
    *,
    is_all_day: bool,
) -> datetime.datetime | None:
    """Get corrected end date for all-day events."""
    if not end:
        return None
    if is_all_day:
        # Subtract 1 day from all-day event end dates
        end -= datetime.timedelta(days=1)
    return end


class GoogleCalendar(BaseComponent):
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    TOKEN_FILE = BaseComponent.credentials_dir() / ".google_calendar_token.json"
    CREDS_FILE = BaseComponent.credentials_dir() / "google_calendar_credentials.json"

    def __init__(self, calendar_config, *args, title="Upcoming Events", **kwargs):
        super().__init__(name="google_calendar", *args, **kwargs)
        self.calendar_config = calendar_config
        self.title = title

    def layout(self):
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-interval-fetch",
                    interval=60 * 5 * 1_000,  # 5 minutes
                ),
                dcc.Store(
                    id=f"{self.component_id}-store",
                    data=None,
                ),
                html.Div(
                    id=f"{self.component_id}-events",
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "stretch",
                        "gap": "8px",
                        "width": "100%",
                        "color": COLORS["pure_white"],
                        "fontFamily": "'Inter', 'Roboto', 'Segoe UI', 'Helvetica Neue', sans-serif",
                    },
                ),
            ],
        )

    @cache_json(valid_lifetime=datetime.timedelta(hours=1))
    def fetch(self) -> list[dict]:
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
        @app.callback(
            Output(f"{self.component_id}-events", "children"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
        )
        def render_events(_):
            data = self.fetch()
            if not data or len(data) == 0:
                return html.Div(
                    "No upcoming events",
                    style={
                        "fontSize": "1.2rem",
                        "color": COLORS["soft_gray"],
                        "textAlign": "center",
                        "padding": "2rem",
                    },
                )

            # Calendar colors for different calendars
            calendar_colors = [
                COLORS["primary_blue"],
                COLORS["warm_orange"],
                COLORS["success_green"],
                COLORS["accent_gold"],
                COLORS["soft_gray"],
                COLORS["dimmed_gray"],
            ]

            # Build calendar ID order for consistent coloring
            calendar_id_order = []
            for event in data:
                calendar_id = event.get("calendarId", "")
                if calendar_id and calendar_id not in calendar_id_order:
                    calendar_id_order.append(calendar_id)

            event_cards = []

            for event in data:
                start_dict = event.get("start", {})
                end_dict = event.get("end", {})
                summary = event.get("summary", "No Title")
                calendar_id = event.get("calendarId", "")

                is_all_day = "dateTime" not in start_dict
                is_birthday = "birthday" in summary.lower()

                start_datetime_str = start_dict.get(
                    "dateTime",
                    start_dict.get(
                        "date",
                    ),
                )
                start_datetime = datetime_from_str(
                    start_datetime_str,
                    is_all_day=is_all_day,
                )

                end_datetime_str = end_dict.get("dateTime", end_dict.get("date"))
                raw_end_datetime = datetime_from_str(
                    end_datetime_str,
                    is_all_day=is_all_day,
                )
                end_datetime = get_corrected_end_date(
                    raw_end_datetime,
                    is_all_day=is_all_day,
                )

                event_is_today = is_today(start_datetime)
                event_is_tomorrow = is_tomorrow(start_datetime)

                # Get calendar color
                color_idx = (
                    calendar_id_order.index(calendar_id)
                    if calendar_id in calendar_id_order
                    else 0
                )
                dot_color = calendar_colors[color_idx % len(calendar_colors)]

                # Format date display
                date_text = format_datetime(start_datetime, is_all_day=is_all_day)

                # Add end date for multi-day events
                if is_multi_day(start_datetime, end_datetime):
                    end_text = format_datetime(end_datetime, is_all_day=is_all_day)
                    date_text += f" → {end_text}"

                # Card styling - clean and minimal with subtle gradient
                card_style = {
                    "background": "linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.06))" if event_is_today 
                                 else "linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
                    "border": f"1px solid {COLORS['accent_gold']}" if event_is_today else "1px solid rgba(255,255,255,0.08)",
                    "borderRadius": "8px",
                    "padding": "2px 4px",
                    "marginBottom": "0",
                    "backdropFilter": "blur(10px)",
                }
                # Text colors - clean and readable
                title_color = COLORS["pure_white"]
                event_card = html.Div(
                    [
                        html.Div(
                            className="test-m centered-content",
                            children=[
                                html.Div(
                                    [
                                        html.Div(
                                            style={
                                                "width": "10px",
                                                "height": "10px",
                                                "borderRadius": "50%",
                                                "background": dot_color,
                                                "marginRight": "10px",
                                                "flexShrink": "0",
                                                "opacity": "0.8",
                                            },
                                            title=calendar_id,
                                        ),
                                        *(
                                            [
                                                DashIconify(
                                                    icon="mdi:cake-variant",
                                                    style={
                                                        "fontSize": "1.1rem",
                                                        "marginRight": "6px",
                                                        "color": COLORS["warm_orange"],
                                                    },
                                                ),
                                            ] if is_birthday else []
                                        ),
                                        html.Span(
                                            summary,
                                            style={
                                                "fontWeight": "bold" if event_is_today else "500",
                                                "fontSize": "1.1rem",
                                                "color": title_color,
                                                "overflow": "hidden",
                                                "textOverflow": "ellipsis",
                                                "whiteSpace": "nowrap",
                                                "lineHeight": "1.2",
                                                "flex": "1",
                                            },
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "overflow": "hidden",
                                        "flex": "1",
                                    },
                                ),
                                html.Div(
                                    date_text,
                                    style={
                                        "fontSize": "1rem",
                                        "color": COLORS["warm_orange"],
                                        "fontWeight": "500",
                                        "marginLeft": "16px",
                                        "whiteSpace": "nowrap",
                                        "textAlign": "right",
                                    },
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "space-between",
                                "width": "100%",
                                "gap": "8px",
                            },
                        ),
                    ],
                    style=card_style,
                )

                event_cards.append(event_card)

            return event_cards
