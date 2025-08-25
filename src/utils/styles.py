"""Centralized styling utilities for Magic Mirror components.
Works in conjunction with src/assets/main.css for compact Pi Zero display.
"""

from typing import Any

# Color palette
COLORS = {
    "blue": "#4A90E2",
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

# Common compact style combinations for Python components
COMPACT_STYLES = {
    "base_container": {
        "fontFamily": "Arial, sans-serif",
        "background": COLORS["black"],
        "lineHeight": "1.1",
        "width": "100vw",
        "height": "100vh",
        "overflow": "hidden",
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
