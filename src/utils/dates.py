import datetime
import os

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


# Centralized timezone for the app. Read once at import.
# Prefer explicit APP_TIMEZONE, fall back to TZ, else UTC.
_APP_TZ_NAME = os.environ.get("APP_TIMEZONE") or os.environ.get("TZ") or "UTC"
_APP_TZ = None
if ZoneInfo is not None:
    try:
        _APP_TZ = ZoneInfo(_APP_TZ_NAME)
    except Exception:  # invalid tz -> fallback to UTC
        _APP_TZ = datetime.UTC
else:
    _APP_TZ = datetime.UTC


def get_app_timezone() -> datetime.tzinfo:
    """Return the application's timezone loaded from env.

    Env vars checked: APP_TIMEZONE, then TZ. Defaults to UTC.
    """
    return _APP_TZ  # type: ignore[return-value]


def local_now() -> datetime.datetime:
    """Timezone-aware now() in the application timezone."""
    return datetime.datetime.now(tz=get_app_timezone())


def local_today() -> datetime.date:
    """Today's date in the application timezone."""
    return local_now().date()


def utc_now() -> datetime.datetime:
    """Timezone-aware now() in UTC."""
    return datetime.datetime.now(tz=datetime.UTC)


def datetime_from_str(datetime_str: str, *, is_all_day: bool) -> datetime.datetime:
    """Convert ISO datetime string to datetime object.

    Args:
        datetime_str: ISO format datetime string
        is_all_day: Whether this is an all-day event

    Returns:
        Parsed datetime object

    """
    if is_all_day:
        # Keep as local midnight naive or attach app tz? Use app tz-aware at midnight.
        return datetime.datetime.fromisoformat(datetime_str + "T00:00:00").replace(
            tzinfo=get_app_timezone(),
        )
    return datetime.datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))


def format_datetime(date_obj: datetime.datetime, *, is_all_day: bool) -> str:
    """Format date/time for display.

    Args:
        date_obj: Datetime object to format
        is_all_day: Whether this is an all-day event

    Returns:
        Formatted datetime string for display

    """
    if is_all_day:
        # For all-day events, show only the date
        return date_obj.strftime("%a %d %b")
    return date_obj.strftime("%a %d %b %H:%M")


def is_today(date_obj: datetime.datetime) -> bool:
    """Check if event is today.

    Args:
        date_obj: Datetime object to check

    Returns:
        True if the date is today or earlier

    """
    return date_obj.date() <= local_today()


def is_tomorrow(date_obj: datetime.datetime) -> bool:
    """Check if event is tomorrow.

    Args:
        date_obj: Datetime object to check

    Returns:
        True if the date is tomorrow

    """
    return date_obj.date() == (local_today() + datetime.timedelta(days=1))


def is_this_week(date_obj: datetime.datetime) -> bool:
    """Check if event is this week.

    Args:
        date_obj: Datetime object to check

    Returns:
        True if the date is within the current week

    """
    today = local_today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    return start_of_week <= date_obj.date() <= end_of_week


def _opacity_from_days_away(
    date_obj: datetime.datetime | datetime.date | None,
) -> float:
    if not date_obj:
        return 0.5

    now = utc_now()

    if isinstance(date_obj, datetime.date) and not isinstance(
        date_obj,
        datetime.datetime,
    ):
        now = now.date()  # type: ignore[assignment]
    elif not hasattr(date_obj, "tzinfo") or date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=now.tzinfo)  # type: ignore[attr-defined]

    days_away = (date_obj - now).days  # type: ignore[operator]

    if days_away <= 1:
        return 1
    if days_away < 3:
        return 0.9
    if days_away < 7:
        return 0.8
    if days_away < 14:
        return 0.6
    return 0.5
