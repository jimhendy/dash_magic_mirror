"""Calendar-related utility functions that can be used by multiple components."""


def truncate_event_title(title: str, max_length: int = 30) -> str:
    """Truncate event title if too long.

    Args:
        title: Original event title
        max_length: Maximum allowed length

    Returns:
        Truncated title with ellipsis if needed

    """
    if len(title) <= max_length:
        return title
    return title[: max_length - 3] + "..."


def get_event_color_by_calendar(calendar_id: str) -> str:
    """Get event color based on calendar ID.

    Args:
        calendar_id: Google Calendar ID

    Returns:
        CSS color string

    """
    # Simple hash-based color assignment
    color_palette = [
        "rgba(74, 144, 226, 0.7)",  # Blue
        "rgba(76, 175, 80, 0.7)",  # Green
        "rgba(255, 152, 0, 0.7)",  # Orange
        "rgba(156, 39, 176, 0.7)",  # Purple
        "rgba(244, 67, 54, 0.7)",  # Red
        "rgba(255, 193, 7, 0.7)",  # Amber
        "rgba(96, 125, 139, 0.7)",  # Blue Grey
    ]

    # Use hash of calendar ID to select color
    color_index = hash(calendar_id) % len(color_palette)
    return color_palette[color_index]


# Global color assignment tracking
_event_color_assignments = {}
_color_counter = 0


def get_event_color_by_event(event_id: str) -> str:
    """Get event color based on event ID with systematic cycling through palette.

    Args:
        event_id: Unique event identifier

    Returns:
        CSS color string

    """
    global _event_color_assignments, _color_counter

    # If we've already assigned a color to this event, return it
    if event_id in _event_color_assignments:
        return _event_color_assignments[event_id]

    # Color palette organized to maximize visual distinction between consecutive colors
    # Arranged by alternating hue families: blue -> green -> red -> purple -> orange -> teal, etc.
    color_palette = [
        "rgba(74, 144, 226, 0.9)",  # Blue
        "rgba(76, 175, 80, 0.9)",  # Green
        "rgba(244, 67, 54, 0.9)",  # Red
        "rgba(103, 58, 183, 0.9)",  # Deep Purple
        "rgba(255, 152, 0, 0.9)",  # Orange
        "rgba(0, 150, 136, 0.9)",  # Teal
        "rgba(233, 30, 99, 0.9)",  # Pink
        "rgba(139, 195, 74, 0.9)",  # Light Green
        "rgba(63, 81, 181, 0.9)",  # Indigo
        "rgba(255, 193, 7, 0.9)",  # Amber
        "rgba(0, 188, 212, 0.9)",  # Cyan
        "rgba(156, 39, 176, 0.9)",  # Purple
        "rgba(121, 85, 72, 0.9)",  # Brown
        "rgba(205, 220, 57, 0.9)",  # Lime
        "rgba(96, 125, 139, 0.9)",  # Blue Grey
        "rgba(255, 87, 34, 0.9)",  # Deep Orange
        "rgba(158, 158, 158, 0.9)",  # Grey
        "rgba(255, 235, 59, 0.9)",  # Yellow
    ]

    # Assign the next color in sequence
    color = color_palette[_color_counter % len(color_palette)]
    _event_color_assignments[event_id] = color
    _color_counter += 1

    return color


def assign_event_colors_consistently(events: list, reference_date=None) -> None:
    """Assign colors to events consistently based on their relationship to a reference date.
    
    Args:
        events: List of events with id, start_datetime attributes
        reference_date: Reference date (defaults to today)
    """
    import datetime
    
    if reference_date is None:
        reference_date = datetime.date.today()
    
    global _event_color_assignments, _color_counter
    
    # Reset assignments
    reset_event_color_assignments()
    
    # Sort events: today events first, then by start date and title
    def sort_key(event):
        event_date = event.start_datetime.date()
        is_today = event_date == reference_date
        is_yesterday = event_date == reference_date - datetime.timedelta(days=1)
        is_multi_day = event.start_datetime.date() != event.end_datetime.date()
        
        # Priority: today events first, then multi-day events that include today,
        # then future events, then yesterday events (if they don't span to today)
        if is_today or (is_multi_day and event_date <= reference_date <= event.end_datetime.date()):
            priority = 0  # Highest priority
        elif event_date > reference_date:
            priority = 1  # Future events
        elif is_yesterday and not is_multi_day:
            priority = 2  # Yesterday single-day events (lowest priority)
        else:
            priority = 3  # Other past events
        
        return (priority, event_date, event.title)
    
    # Sort and assign colors
    sorted_events = sorted(events, key=sort_key)
    
    # Pre-assign colors to ensure consistency
    for event in sorted_events:
        get_event_color_by_event(event.id)


def reset_event_color_assignments():
    """Reset the event color assignments for a fresh start."""
    global _event_color_assignments, _color_counter
    _event_color_assignments = {}
    _color_counter = 0


def get_contrasting_text_color(background_color: str) -> str:
    """Calculate contrasting text color based on background color.

    Args:
        background_color: CSS color string (rgba format)

    Returns:
        CSS color string for contrasting text

    """
    # Extract RGB values from rgba string
    # Format: "rgba(r, g, b, a)"
    try:
        # Remove "rgba(" and ")" and split by comma
        rgb_part = background_color.replace("rgba(", "").replace(")", "")
        r, g, b, a = [float(x.strip()) for x in rgb_part.split(",")]

        # Calculate luminance using standard formula
        # Convert to 0-1 scale if needed
        if r > 1 or g > 1 or b > 1:
            r, g, b = r / 255, g / 255, b / 255

        # Calculate relative luminance
        def luminance_component(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        luminance = (
            0.2126 * luminance_component(r)
            + 0.7152 * luminance_component(g)
            + 0.0722 * luminance_component(b)
        )

        # Return black for light backgrounds, white for dark backgrounds
        return "#000000" if luminance > 0.5 else "#FFFFFF"

    except (ValueError, IndexError):
        # Fallback to black if parsing fails
        return "#000000"
