import datetime
import os
from dataclasses import dataclass

from dash import Input, Output, dcc, html
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from components.base import BaseComponent


@dataclass
class CalendarConfig:
    calendar_ids: list[str]
    max_events: int = 10


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
                    interval=300_000,  # 5 minutes
                ),
                dcc.Store(
                    id=f"{self.component_id}-store",
                    data=None,
                ),
                html.Div(
                    id=f"{self.component_id}-events",
                    style={"display": "flex", "flexDirection": "column"},
                ),
            ],
            style={"color": "#FFFFFF"},
        )

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
            Output(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
        )
        def fetch_data(n_intervals):
            return self.fetch()

        # Assign a color to each calendarId (fixed palette)

        app.clientside_callback(
            f"""
            function(data, n_intervals) {{
                const container = document.getElementById('{self.component_id}-events');
                const calendarColors = [
                    '#4A90E2', // blue
                    '#FF6B6B', // red
                    '#FFD93D', // yellow
                    '#6BCF7F', // green
                    '#A259FF', // purple
                    '#FFB86C', // orange
                    '#00B8D9', // teal
                    '#FF5CA7', // pink
                ];
                if (!container) return window.dash_clientside.no_update;
                container.innerHTML = '';
                if (!data || !Array.isArray(data) || data.length === 0) {{
                    const empty = document.createElement('div');
                    empty.textContent = 'No upcoming events.';
                    empty.style.textAlign = 'center';
                    empty.style.opacity = 0.7;
                    container.appendChild(empty);
                    return window.dash_clientside.no_update;
                }}
                // Build a unique list of calendarIds in order of appearance
                const calendarIdOrder = [];
                data.forEach(ev => {{
                    if (ev.calendarId && !calendarIdOrder.includes(ev.calendarId)) {{
                        calendarIdOrder.push(ev.calendarId);
                    }}
                }});
                for (let i = 0; i < data.length; i++) {{
                    const event = data[i];
                    const start = event.start.dateTime || event.start.date;
                    const summary = event.summary || 'No Title';
                    const calendarId = event.calendarId || '';
                    const colorIdx = Math.max(0, calendarIdOrder.indexOf(calendarId)) % calendarColors.length;
                    const dotColor = calendarColors[colorIdx];
                    const eventDiv = document.createElement('div');
                    eventDiv.style.cssText = `
                        padding: 10px 16px;
                        margin-bottom: 8px;
                        background: rgba(255,255,255,0.07);
                        border-radius: 7px;
                        border: 1px solid rgba(74,144,226,0.18);
                        font-size: 1.1rem;
                        display: flex;
                        flex-direction: row;
                        align-items: center;
                        justify-content: space-between;
                    `;
                    // Colored dot
                    const dot = document.createElement('span');
                    dot.style.display = 'inline-block';
                    dot.style.width = '14px';
                    dot.style.height = '14px';
                    dot.style.borderRadius = '50%';
                    dot.style.background = dotColor;
                    dot.style.marginRight = '12px';
                    dot.title = calendarId;
                    // Time
                    const timeSpan = document.createElement('span');
                    timeSpan.textContent = start.replace('T', ' ').replace(/:00(\\.\\d+)?Z?$/, '');
                    timeSpan.style.color = '#4A90E2';
                    timeSpan.style.fontWeight = '500';
                    timeSpan.style.marginRight = '12px';
                    // Summary
                    const summarySpan = document.createElement('span');
                    summarySpan.textContent = summary;
                    summarySpan.style.flex = '1';
                    summarySpan.style.color = '#FFFFFF';
                    summarySpan.style.fontWeight = '400';
                    eventDiv.appendChild(dot);
                    eventDiv.appendChild(timeSpan);
                    eventDiv.appendChild(summarySpan);
                    container.appendChild(eventDiv);
                }}
                return window.dash_clientside.no_update;
            }}
            """,
            Output(f"{self.component_id}-events", "children"),
            Input(f"{self.component_id}-store", "data"),
            Input(f"{self.component_id}-interval-fetch", "n_intervals"),
            prevent_initial_call=True,
        )
