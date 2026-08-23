"""Maps WeatherAPI condition text to a sleek vector icon + color.

WeatherAPI's own icons (bitmap PNGs served from their CDN) are small,
dated-looking cartoon graphics and are the odd one out visually - every
other icon in this app is a crisp `mdi:*` glyph via DashIconify. This module
keyword-matches the condition text (rather than the numeric condition code,
which would need the full ~40-entry table from WeatherAPI's docs) onto the
same icon family used everywhere else, so weather actually looks like part
of the same app instead of an embedded widget.
"""

from __future__ import annotations

from utils.styles import COLORS

# (icon, color) - color chosen to read at a glance: warm for sun/heat, the
# app's one accent for rain/water, neutral grays for cloud/fog, white-ish
# for snow, urgent-red only for storms (genuinely the most severe condition).
_ICON_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("thunder",), "mdi:weather-lightning", COLORS["urgent"]),
    (("blizzard", "heavy snow"), "mdi:weather-snowy-heavy", COLORS["text"]),
    (("snow", "sleet", "ice pellet"), "mdi:weather-snowy", COLORS["text"]),
    (
        ("freezing drizzle", "freezing rain"),
        "mdi:weather-snowy-rainy",
        COLORS["accent"],
    ),
    (
        ("heavy rain", "torrential", "heavy shower", "heavy drizzle"),
        "mdi:weather-pouring",
        COLORS["accent"],
    ),
    (("rain", "drizzle", "shower"), "mdi:weather-rainy", COLORS["accent"]),
    (("fog", "mist"), "mdi:weather-fog", COLORS["text_secondary"]),
    (("overcast",), "mdi:weather-cloudy", COLORS["text_secondary"]),
]


def get_weather_icon(
    condition_text: str | None, *, is_day: bool = True,
) -> tuple[str, str]:
    """Resolve a WeatherAPI condition string to an (icon_name, color) pair."""
    text = (condition_text or "").lower()

    for keywords, icon, color in _ICON_RULES:
        if any(word in text for word in keywords):
            return icon, color

    if "cloud" in text:
        icon = (
            "mdi:weather-partly-cloudy" if is_day else "mdi:weather-night-partly-cloudy"
        )
        return icon, COLORS["text_secondary"]

    if "clear" in text or "sunny" in text:
        icon = "mdi:weather-sunny" if is_day else "mdi:weather-night"
        return icon, COLORS["gold"] if is_day else COLORS["text_secondary"]

    # Unknown condition text: a safe, neutral default.
    return "mdi:weather-partly-cloudy", COLORS["text_secondary"]
