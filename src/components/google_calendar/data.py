"""Data fetching and processing for Google Calendar component."""

import asyncio
import datetime
from dataclasses import dataclass
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from components.base import BaseComponent
from utils.dates import datetime_from_str, local_now, local_today
from utils.file_cache import cache_json


@dataclass
class CalendarEvent:
    """Processed calendar event data."""

    id: str
    title: str
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    is_all_day: bool
    is_multi_day: bool
    starts_before_today: bool
    ends_after_tomorrow: bool
    calendar_id: str


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_FILE = BaseComponent.credentials_dir() / ".google_calendar_token.json"
CREDS_FILE = BaseComponent.credentials_dir() / "google_calendar_credentials.json"


@cache_json(valid_lifetime=datetime.timedelta(minutes=5))
def fetch_calendar_events(
    calendar_ids: list[str],
) -> list[dict[str, Any]]:
    """Fetch events from Google Calendar API.

    Args:
        calendar_ids: List of Google Calendar IDs to fetch events from

    Returns:
        List of raw event dictionaries from the Google Calendar API

    """
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                logger.error("Google Calendar credentials file not found")
                return []
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Get events from yesterday to next week to handle multi-day events
        yesterday = (local_now() - datetime.timedelta(days=1)).isoformat()
        end_date = (local_now() + datetime.timedelta(days=7 * 5)).isoformat()

        events = []
        for calendar_id in calendar_ids:
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=yesterday,
                    timeMax=end_date,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            for event in events_result.get("items", []):
                event["calendarId"] = calendar_id
                events.append(event)

        # Sort all events by start time
        events.sort(
            key=lambda e: e["start"].get("dateTime", e["start"].get("date", "")),
        )

        return events

    except HttpError as error:
        logger.error(f"Google Calendar API error: {error}")
        return []


async def async_fetch_calendar_events(
    calendar_ids: list[str],
) -> list[dict[str, Any]]:
    """Async wrapper around :func:`fetch_calendar_events`."""
    return await asyncio.to_thread(fetch_calendar_events, calendar_ids)


def process_calendar_events(
    raw_events: list[dict[str, Any]],
    *,
    truncate_to_tomorrow: bool,
) -> list[CalendarEvent]:
    """Process raw calendar events into structured data.

    Args:
        raw_events: Raw event dictionaries from Google Calendar API
        truncate_to_tomorrow: Whether to truncate events to tomorrow

    Returns:
        List of processed CalendarEvent objects

    """
    processed_events = []
    today = local_today()
    tomorrow = today + datetime.timedelta(days=1)

    for event in raw_events:
        # Extract event details
        event_id = event.get("id", "")
        title = event.get("summary", "Untitled Event")

        # Parse start and end times
        start_data = event.get("start", {})
        end_data = event.get("end", {})

        is_all_day = "date" in start_data

        if is_all_day:
            start_str = start_data.get("date", "")
            end_str = end_data.get("date", "")
        else:
            start_str = start_data.get("dateTime", "")
            end_str = end_data.get("dateTime", "")

        if not start_str or not end_str:
            continue

        start_datetime = datetime_from_str(start_str, is_all_day=is_all_day)
        end_datetime = datetime_from_str(end_str, is_all_day=is_all_day)

        # For all-day events, Google Calendar sets end date to the day after
        if is_all_day:
            end_datetime = end_datetime - datetime.timedelta(days=1)

        # Determine event characteristics
        is_multi_day = start_datetime.date() != end_datetime.date()
        starts_before_today = start_datetime.date() < today
        ends_after_tomorrow = end_datetime.date() > tomorrow

        # Only include events that are relevant to today/tomorrow
        event_touches_today_tomorrow = (
            start_datetime.date() <= tomorrow and end_datetime.date() >= today
        )

        if not event_touches_today_tomorrow and truncate_to_tomorrow:
            continue

        processed_events.append(
            CalendarEvent(
                id=event_id,
                title=title,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                is_all_day=is_all_day,
                is_multi_day=is_multi_day,
                starts_before_today=starts_before_today,
                ends_after_tomorrow=ends_after_tomorrow,
                calendar_id=event.get("calendarId", ""),
            ),
        )

    return processed_events


def get_events_for_date(
    events: list[CalendarEvent],
    target_date: datetime.date,
) -> list[CalendarEvent]:
    """Get events that occur on a specific date.

    Args:
        events: List of processed calendar events
        target_date: Date to filter events for

    Returns:
        List of events that occur on the target date

    """
    return [
        event
        for event in events
        if event.start_datetime.date() <= target_date <= event.end_datetime.date()
    ]
