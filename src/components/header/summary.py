"""Summary rendering helpers for Header component.

Currently minimal because the header layout is defined inside the component.
This module exists for parity with other components and future extension.
"""

from __future__ import annotations

from dash import html

from utils.styles import COLORS, FONT_SIZES, WEIGHT

from .data import PersonPresence


def render_presence_badges(people: list[PersonPresence]):
    return [_person_badge(p) for p in people]


def _person_badge(person: PersonPresence):
    # One person per line, stacked in the top-right corner to mirror the
    # markets widget pinned top-left: same secondary/bold weight as the
    # markets figures so home-status reads at the same level of prominence.
    is_home = getattr(person, "is_home", False)
    dot_style = {
        "width": "0.65rem",
        "height": "0.65rem",
        "borderRadius": "50%",
        "background": COLORS["accent"] if is_home else "transparent",
        "border": f"1.5px solid {COLORS['accent'] if is_home else COLORS['text_muted']}",
        "flexShrink": 0,
    }
    return html.Div(
        [
            html.Div(style=dot_style),
            html.Div(
                person.name,
                style={
                    "fontSize": FONT_SIZES["secondary"],
                    "fontWeight": WEIGHT["bold"],
                    "color": COLORS["text"] if is_home else COLORS["text_muted"],
                },
            ),
        ],
        style={"display": "flex", "alignItems": "center", "gap": "0.5rem"},
    )


__all__ = ["render_presence_badges"]
