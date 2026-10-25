"""Design tokens shared by Python render code.

Almost all styling lives in `assets/main.css` as classes (so it can use
media queries for portrait/landscape and stay out of the serialized
component tree). The few places Python still needs a literal color - data
driven colors such as a TfL line's brand color, weather icon tints, Plotly
figures - read them from here. Keep these in sync with the `:root` custom
properties at the top of `main.css`.
"""

from __future__ import annotations

COLORS: dict[str, str] = {
    "bg": "#0A0C10",
    "surface": "#13161D",
    "surface_raised": "#1A1E27",
    "hairline": "rgba(255, 255, 255, 0.06)",
    "hairline_strong": "rgba(255, 255, 255, 0.12)",
    "text": "#F2F4F7",
    "text_secondary": "#A0A8B6",
    "text_muted": "#626B7A",
    # The one brand accent: "now / today / live / good".
    "accent": "#5EEAD4",
    "blue": "#7AA7FF",
    "violet": "#B69CFF",
    "gold": "#F5C35B",
    "orange": "#FF9F5A",
    # Reserved for genuinely time-critical states (imminent arrival,
    # disruption, overdue) - never decorative.
    "urgent": "#FF6B6B",
    "black": "#0A0C10",
    "white": "#F2F4F7",
}

FONT_FAMILY = "'Inter', -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

# Calendar colours, assigned by the order calendars are configured in, so
# a given calendar keeps the same colour across refreshes and restarts
# (Python's own `hash()` of a string is salted per process, so it can't be
# used for this).
CALENDAR_PALETTE: list[str] = [
    "#7AA7FF",
    "#5EEAD4",
    "#F5C35B",
    "#B69CFF",
    "#FF9F5A",
    "#F28DB2",
    "#9BD772",
]


def with_alpha(hex_color: str, alpha: float) -> str:
    """`#RRGGBB` -> `rgba(r, g, b, alpha)`."""
    hex_color = hex_color.lstrip("#")
    try:
        r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return hex_color
    return f"rgba({r}, {g}, {b}, {alpha})"


def contrast_text(hex_color: str) -> str:
    """Near-black or white, whichever reads better on `hex_color`."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    except (ValueError, IndexError):
        return COLORS["text"]
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#0A0C10" if luminance > 0.55 else "#FFFFFF"
