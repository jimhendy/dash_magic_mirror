"""Small markup builders shared by every component's tile/detail renderers.

These only assemble class names - the look itself is defined in
`assets/main.css`.
"""

from __future__ import annotations

from typing import Any

from dash import html
from dash_iconify import DashIconify


def icon(name: str, class_name: str = "ic", color: str | None = None) -> DashIconify:
    style = {"color": color} if color else None
    return DashIconify(icon=name, className=class_name, style=style)


def empty_state(message: str, icon_name: str = "mdi:check-circle-outline") -> html.Div:
    return html.Div(
        [icon(icon_name, "empty__icon"), html.Span(message)],
        className="empty",
    )


def placeholder(message: str) -> html.Div:
    """Loading / error state shown inside a tile or panel body."""
    return html.Div(
        [
            html.Div(className="skeleton"),
            html.Div(message, className="placeholder__text"),
        ],
        className="placeholder",
    )


def badge(text: str, tone: str = "neutral", icon_name: str | None = None) -> html.Span:
    """Small status pill. `tone`: neutral | good | warn | bad | info."""
    children: list[Any] = [icon(icon_name, "badge__icon")] if icon_name else []
    children.append(text)
    return html.Span(children, className=f"badge badge--{tone}")


def section(
    title: str, children: Any, *, extra: Any = None, class_name: str = ""
) -> html.Section:
    """A titled block inside a detail panel."""
    head = [html.H3(title, className="section__title")]
    if extra is not None:
        head.append(extra)
    return html.Section(
        [html.Div(head, className="section__head"), children],
        className=f"section {class_name}".strip(),
    )


def stat(label: str, value: Any, icon_name: str | None = None) -> html.Div:
    return html.Div(
        [
            html.Div(
                [icon(icon_name, "stat__icon")] if icon_name else [],
                className="stat__icon-wrap",
            )
            if icon_name
            else None,
            html.Div(
                [
                    html.Div(label, className="stat__label"),
                    html.Div(value, className="stat__value"),
                ],
            ),
        ],
        className="stat",
    )


def filter_chips(group: str, options: list[tuple[str, str]]) -> html.Div:
    """Client-side filter control (see `assets/dashboard.js`): items inside the
    same panel carrying `data-filter-key` are shown/hidden to match the
    selected chip. `options` is a list of (value, label); "all" is prepended.
    """
    chips = [("all", "All"), *options]
    return html.Div(
        [
            html.Button(
                label,
                className="chip" + (" is-active" if value == "all" else ""),
                **{"data-filter-value": value},
            )
            for value, label in chips
        ],
        className="chips",
        **{"data-filter-group": group},
    )
