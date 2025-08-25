import datetime


def datetime_from_str(datetime_str: str, *, is_all_day: bool) -> datetime.datetime:
    """Convert ISO datetime string to datetime object.

    Args:
        datetime_str: ISO format datetime string
        is_all_day: Whether this is an all-day event

    Returns:
        Parsed datetime object

    """
    if is_all_day:
        return datetime.datetime.fromisoformat(datetime_str + "T00:00:00")
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
    return date_obj.date() <= datetime.date.today()


def is_tomorrow(date_obj: datetime.datetime) -> bool:
    """Check if event is tomorrow.

    Args:
        date_obj: Datetime object to check

    Returns:
        True if the date is tomorrow

    """
    return date_obj.date() == (datetime.date.today() + datetime.timedelta(days=1))


def is_this_week(date_obj: datetime.datetime) -> bool:
    """Check if event is this week.

    Args:
        date_obj: Datetime object to check

    Returns:
        True if the date is within the current week

    """
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    return start_of_week <= date_obj.date() <= end_of_week


def _opacity_from_days_away(
    date_obj: datetime.datetime | datetime.date | None,
) -> float:
    if not date_obj:
        return 0.5

    now = datetime.datetime.now(tz=datetime.UTC)

    if isinstance(date_obj, datetime.date) and not isinstance(
        date_obj,
        datetime.datetime,
    ):
        now = now.date()
    elif not hasattr(date_obj, "tzinfo") or date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=now.tzinfo)

    days_away = (date_obj - now).days

    if days_away <= 1:
        return 1
    if days_away < 3:
        return 0.9
    if days_away < 7:
        return 0.8
    if days_away < 14:
        return 0.6
    return 0.5
