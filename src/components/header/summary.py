"""Presence badge rendering for the Header component."""

from __future__ import annotations

from dash import html

from .data import PersonPresence


def render_presence_badges(people: list[PersonPresence]):
    return [_person_badge(p) for p in people]


def _person_badge(person: PersonPresence):
    is_home = getattr(person, "is_home", False)
    initial = (person.name[:1] or "?").upper()
    return html.Div(
        [
            html.Span(initial, className="person__avatar"),
            html.Div(
                [
                    html.Span(person.name, className="person__name"),
                    html.Span("Home" if is_home else "Away", className="person__state"),
                ],
                className="person__text",
            ),
        ],
        className="person" + (" is-home" if is_home else ""),
    )


__all__ = ["render_presence_badges"]
