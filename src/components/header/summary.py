"""Summary rendering helpers for Header component.

Currently minimal because the header layout is defined inside the component.
This module exists for parity with other components and future extension.
"""
from __future__ import annotations

from dash import html
from .data import PersonPresence
from utils.styles import FONT_SIZES, COLORS


def render_presence_badges(people: list[PersonPresence]):
    return [ _person_badge(p) for p in people ]


def _person_badge(person: PersonPresence):
    is_home = getattr(person, "is_home", False)
    color_home = COLORS.get("green", "#32CD32")
    color_away = COLORS.get("red", "#ff4d4d")
    color = color_home if is_home else color_away
    fill = color if is_home else "transparent"
    circle_style = {
        "width": "18px",
        "height": "18px",
        "borderRadius": "50%",
        "border": f"2px solid {color}",
        "background": fill,
        "boxShadow": "0 0 6px rgba(0,255,0,0.6)" if is_home else "none",
        "flexShrink": 0,
    }
    return html.Div(
        [
            html.Div(style=circle_style),
            html.Div(
                person.name,
                style={
                    "fontSize": FONT_SIZES["summary_secondary"],
                    "fontWeight": 500,
                    "opacity": 1.0 if is_home else 0.55,
                },
            ),
        ],
        style={
            "display": "flex",
            "alignItems": "center",
            "gap": "6px",
            "padding": "2px 6px",
            "borderRadius": "4px",
            "background": "rgba(255,255,255,0.04)" if is_home else "transparent",
        },
    )

__all__ = ["render_presence_badges"]
