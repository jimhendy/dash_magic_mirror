from __future__ import annotations

import time

from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.styles import COLORS

from .constants import (
    DEFAULT_ARP_TIMEOUT,
    DEFAULT_GRACE_SECONDS,
    DEFAULT_PING_ATTEMPTS,
    DEFAULT_PING_WAIT,
    PRESENCE_POLL_INTERVAL_MS,
)
from .data import (
    PersonPresence,
    _norm,
    update_people_presence_by_ip,
)
from .full_screen import render_header_fullscreen
from .summary import render_presence_badges


class Header(BaseComponent):
    PRESENCE_POLL_INTERVAL_MS = PRESENCE_POLL_INTERVAL_MS

    def __init__(
        self,
        *,
        people: list[PersonPresence],
        grace_seconds: int = DEFAULT_GRACE_SECONDS,
        arp_timeout: int = DEFAULT_ARP_TIMEOUT,
        ping_attempts: int = DEFAULT_PING_ATTEMPTS,
        ping_wait: float = DEFAULT_PING_WAIT,
        **kwargs,
    ):
        super().__init__(name="header", full_screen=False, **kwargs)
        self.people = people
        self.grace_seconds = grace_seconds
        self.arp_timeout = arp_timeout
        self.ping_attempts = ping_attempts
        self.ping_wait = ping_wait
        for p in self.people:
            p.last_seen = 0  # type: ignore[attr-defined]

    def _summary_layout(self):  # type: ignore[override]
        # Container is relative; presence column absolute top-left; hour:minute absolute centered; seconds offset to right.
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-presence-poll",
                    interval=self.PRESENCE_POLL_INTERVAL_MS,
                    n_intervals=0,
                ),
                # Presence badges vertical stack (absolute positioned top-left)
                html.Div(
                    render_presence_badges(self.people),
                    id=f"{self.component_id}-people",
                    style={
                        "position": "absolute",
                        "top": "4px",
                        "left": "4px",
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "6px",
                        "alignItems": "flex-start",
                        "justifyContent": "flex-start",
                        "minWidth": "120px",
                        "zIndex": 2,
                    },
                ),
                # Clock/date layer
                html.Div(
                    [
                        # Date (standard centered block)
                        html.Div(
                            id=f"{self.component_id}-date",
                            style={
                                "fontSize": "1.2rem",
                                "color": COLORS["soft_gray"],
                                "marginBottom": "0.25rem",
                                "textAlign": "center",
                                "width": "100%",
                            },
                        ),
                        # Hour:Minute absolutely centered horizontally
                        html.Div(
                            id=f"{self.component_id}-hour-minute",
                            style={
                                "position": "absolute",
                                "left": "50%",
                                "transform": "translateX(-50%)",
                                "top": "1.8rem",  # below date
                                "fontSize": "5rem",
                                "fontWeight": "350",
                                "color": COLORS["white"],
                                "lineHeight": "1",
                                "whiteSpace": "nowrap",
                                "zIndex": 1,
                            },
                        ),
                        # Seconds positioned to the right of the centered hour:minute without shifting it
                        html.Div(
                            id=f"{self.component_id}-seconds",
                            style={
                                "position": "absolute",
                                # Offset: move to center then shift right by fixed px (tweakable)
                                "left": "calc(50% + 100px)",  # adjust if font/spacing changes
                                "top": "2.1rem",  # align near top of hour digits
                                "fontSize": "1.1rem",
                                "color": COLORS["gray"],
                                "zIndex": 1,
                            },
                        ),
                    ],
                    style={
                        "position": "relative",
                        "width": "100%",
                        "height": "7.5rem",  # enough to contain large digits
                        "display": "block",
                        "margin": "0 auto",
                        "zIndex": 1,
                    },
                ),
            ],
            style={
                "position": "relative",
                "display": "flex",
                "flexDirection": "row",
                "alignItems": "flex-start",
                "justifyContent": "center",
                "padding": "4px 4px 8px 4px",
                "width": "100%",
            },
        )

    def _add_callbacks(self, app):  # type: ignore[override]
        app.clientside_callback(
            """
            function(n_intervals) {
                const now = new Date();
                const date = now.toLocaleDateString('en-UK', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });
                const hours = now.getHours().toString().padStart(2, '0');
                const minutes = now.getMinutes().toString().padStart(2, '0');
                const hourMinute = `${hours}:${minutes}`;
                const seconds = now.getSeconds().toString().padStart(2, '0');
                return [date, hourMinute, seconds];
            }
            """,
            Output(f"{self.component_id}-date", "children"),
            Output(f"{self.component_id}-hour-minute", "children"),
            Output(f"{self.component_id}-seconds", "children"),
            Input("one-second-timer", "n_intervals"),
        )

        @app.callback(
            Output(f"{self.component_id}-people", "children"),
            Input(f"{self.component_id}-presence-poll", "n_intervals"),
        )
        def _update_presence(_n):
            start = time.time()
            now = time.time()
            update_people_presence_by_ip(
                self.people,
                now=now,
                grace_seconds=self.grace_seconds,
                arp_timeout=self.arp_timeout,
                ping_attempts=self.ping_attempts,
                ping_wait=self.ping_wait,
            )
            duration = time.time() - start
            logger.debug(
                f"Header presence scan {duration:.2f}s people={len(self.people)}",
            )
            for person in self.people:
                logger.debug(
                    f"Presence {person.name} mac={_norm(person.mac)} ip={person.ip} home={person.is_home}",
                )
            return render_presence_badges(self.people)

    # Optional future full screen hook
    def full_screen_content(self):  # type: ignore[override]
        return render_header_fullscreen(self.people)
