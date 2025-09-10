"""Full screen view for Header component (placeholder).

For future expansion: could show extended presence history, network stats,
upcoming calendar highlights, etc.
"""
from __future__ import annotations

from dash import html
from utils.models import FullScreenResult
from .data import PersonPresence
from .summary import render_presence_badges


def render_header_fullscreen(people: list[PersonPresence]) -> FullScreenResult:
    # Simple placeholder layout
    return FullScreenResult(
        layout=html.Div(
            [
                html.H2("Status", style={"marginBottom": "12px"}),
                html.Div(render_presence_badges(people), style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
                html.Div("(Header full screen placeholder)", style={"opacity": 0.6, "marginTop": "24px"}),
            ],
            style={
                "padding": "40px",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "flex-start",
            },
        ),
        title="Status",
    )

__all__ = ["render_header_fullscreen"]
