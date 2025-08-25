"""Google Calendar component package.

This package contains a refactored, well-documented, and type-hinted
Google Calendar component for the Magic Mirror application.

The component is split into separate modules for better maintainability:
- layout.py: Layout mixin for component-specific UI
- utils.py: Date/event processing utility functions
- callbacks.py: Dash callback registration and handling
- rendering.py: Visual rendering logic for calendar grids and events

The core modal functionality is handled by the app's core modal system.
"""

# Import main classes from the parent module
import importlib.util
import os

_module_path = os.path.join(os.path.dirname(__file__), "..", "google_calendar.py")
_spec = importlib.util.spec_from_file_location("google_calendar_main", _module_path)
_google_calendar_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_google_calendar_main)

# Import the main classes
GoogleCalendar = _google_calendar_main.GoogleCalendar
CalendarConfig = _google_calendar_main.CalendarConfig

from utils.dates import (
    datetime_from_str,
    format_datetime,
    is_this_week,
    is_today,
    is_tomorrow,
)

from .callbacks import GoogleCalendarCallbacks
from .layout import GoogleCalendarLayoutMixin
from .rendering import GoogleCalendarRenderer
from .utils import (
    generate_calendar_grid,
    get_corrected_end_date,
    get_events_for_date,
    is_multi_day,
    process_multi_day_events,
)

__all__ = [
    "CalendarConfig",
    "GoogleCalendar",
    "GoogleCalendarCallbacks",
    "GoogleCalendarLayoutMixin",
    "GoogleCalendarRenderer",
    "datetime_from_str",
    "format_datetime",
    "generate_calendar_grid",
    "get_corrected_end_date",
    "get_events_for_date",
    "is_multi_day",
    "is_this_week",
    "is_today",
    "is_tomorrow",
    "process_multi_day_events",
]


__all__ = [
    "GoogleCalendarCallbacks",
    "GoogleCalendarLayoutMixin",
    "GoogleCalendarRenderer",
    "datetime_from_str",
    "format_datetime",
    "generate_calendar_grid",
    "get_corrected_end_date",
    "get_events_for_date",
    "is_multi_day",
    "is_this_week",
    "is_today",
    "is_tomorrow",
    "process_multi_day_events",
]
