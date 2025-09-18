"""Centralized styling utilities for Magic Mirror components.
Works in conjunction with src/assets/main.css for compact Pi Zero display.
"""

from typing import Any

# Color palette
COLORS = {
    "blue": "#4A90E2",
    "blue_dimmed": "#6EA8E5",
    "gold": "#FFD700",
    "orange": "#FFA500",
    "red": "#FF0000",
    "dimmed_red": "#FD6A6A",
    "green": "#32CD32",
    "white": "#FFFFFF",
    "soft_gray": "#CCCCCC",
    "black": "#000000",
    "dark_gray": "#333333",
    "light_gray": "#F0F0F0",
    "gray": "#888888",
}

# Centralized font scale tuned for 7" viewing distance (≈1–1.2m)
# Naming is semantic so components don't use raw numeric values.
FONT_SIZES: dict[str, str] = {
    "summary_heading": "1.45rem",  # Section titles / key labels
    "summary_primary": "1.35rem",  # Main data (times, team names, temps)
    "summary_secondary": "1.25rem",  # Secondary labels
    "summary_meta": "0.95rem",  # Subtext / meta info
    "summary_small": "0.85rem",  # Rare very small annotations
}

LINE_HEIGHT_DEFAULT = "1.25"  # Slightly relaxed for legibility

TEXT_STYLES = {
    "heading": {"fontSize": FONT_SIZES["summary_heading"], "fontWeight": "600"},
    "primary": {"fontSize": FONT_SIZES["summary_primary"], "fontWeight": "500"},
    "secondary": {"fontSize": FONT_SIZES["summary_secondary"], "fontWeight": "400"},
    "meta": {
        "fontSize": FONT_SIZES["summary_meta"],
        "fontWeight": "400",
        "opacity": 0.9,
    },
    "small": {
        "fontSize": FONT_SIZES["summary_small"],
        "fontWeight": "400",
        "opacity": 0.85,
    },
}

# Common compact style combinations for Python components
COMPACT_STYLES = {
    "base_container": {
        "background": COLORS["black"],
        "lineHeight": LINE_HEIGHT_DEFAULT,
        "width": "100vw",
        "height": "100vh",
        "position": "relative",
        "left": "0",
        "top": "0",
    },
    "card": {
        "background": COLORS["dark_gray"],
        "border": f"1px solid {COLORS['soft_gray']}",
        "borderRadius": "0.4rem",
        "padding": "0.6rem",
        "marginBottom": "0.3rem",
        "boxShadow": "0 1px 3px rgba(0,0,0,0.2)",
    },
}


def merge_styles(*styles: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple style dictionaries."""
    result = {}
    for style in styles:
        if style:
            result.update(style)
    return result
