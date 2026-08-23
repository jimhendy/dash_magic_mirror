from __future__ import annotations

import asyncio
import time

from dash import Input, Output, dcc, html
from loguru import logger

from components.base import BaseComponent
from utils.data_repository import ComponentPayload, get_repository
from utils.styles import COLORS, hero_style, kicker_style

from .constants import (
    DEFAULT_ARP_TIMEOUT,
    DEFAULT_GRACE_SECONDS,
    DEFAULT_PING_ATTEMPTS,
    DEFAULT_PING_WAIT,
    DEFAULT_PRESENCE_SCAN_INTERVAL_SECONDS,
    PRESENCE_POLL_INTERVAL_MS,
)
from .data import (
    PersonPresence,
    _norm,
    update_people_presence_by_ip,
)
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
        scan_interval_seconds: float = DEFAULT_PRESENCE_SCAN_INTERVAL_SECONDS,
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

        # Presence scanning (ping + ARP) runs once in the shared background
        # repository loop, not per connected browser tab. Every client's
        # own poll interval below just re-renders the latest in-memory
        # state - it never triggers network I/O itself.
        self._repository = get_repository()
        self._presence_data_key = f"{self.name}-presence"
        try:
            self._repository.register_component(
                self._presence_data_key,
                refresh_coro=self._scan_presence,
                interval_seconds=scan_interval_seconds,
            )
            self._repository.refresh_now_sync(self._presence_data_key)
        except ValueError:
            # Already registered (e.g. hot reload) - background loop already running.
            pass

    async def _scan_presence(self) -> ComponentPayload:
        """Background refresher: scan presence for every configured person once."""
        start = time.time()
        await asyncio.to_thread(
            update_people_presence_by_ip,
            self.people,
            now=start,
            grace_seconds=self.grace_seconds,
            arp_timeout=self.arp_timeout,
            ping_attempts=self.ping_attempts,
            ping_wait=self.ping_wait,
        )
        duration = time.time() - start
        logger.debug(f"Header presence scan {duration:.2f}s people={len(self.people)}")
        for person in self.people:
            logger.debug(
                f"Presence {person.name} mac={_norm(person.mac)} ip={person.ip} home={person.is_home}",
            )
        # Only the side effect on `self.people` matters; the payload itself
        # is just a marker so the repository has something to store.
        return ComponentPayload(summary=None)

    def _summary_layout(self):
        return html.Div(
            [
                dcc.Interval(
                    id=f"{self.component_id}-presence-poll",
                    interval=self.PRESENCE_POLL_INTERVAL_MS,
                    n_intervals=0,
                ),
                # Top row: presence on the left, date on the right - plain
                # flow, no absolute positioning or magic offsets.
                html.Div(
                    [
                        html.Div(
                            render_presence_badges(self.people),
                            id=f"{self.component_id}-people",
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "1.1rem",
                            },
                        ),
                        html.Div(
                            id=f"{self.component_id}-date",
                            style=kicker_style(),
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "space-between",
                        "width": "100%",
                    },
                ),
                # Clock: a symmetric 3-column grid (spacer / hour:minute /
                # seconds+spacer) keeps hour:minute genuinely pinned to
                # center regardless of how wide the seconds text renders -
                # centering hour:minute and seconds together as one flex
                # group (the previous approach) shifts the whole group,
                # and with it the hour:minute digits, every time the
                # seconds' rendered width changes.
                html.Div(
                    [
                        html.Div(),  # left spacer, mirrors the right column
                        html.Span(
                            id=f"{self.component_id}-hour-minute",
                            style=hero_style(),
                        ),
                        html.Span(
                            id=f"{self.component_id}-seconds",
                            style={
                                "fontSize": "1.6rem",
                                "fontWeight": "400",
                                "color": COLORS["text_muted"],
                                "marginLeft": "0.6rem",
                                "fontVariantNumeric": "tabular-nums",
                                "justifySelf": "start",
                                "alignSelf": "baseline",
                            },
                        ),
                    ],
                    style={
                        "display": "grid",
                        "gridTemplateColumns": "1fr auto 1fr",
                        "alignItems": "baseline",
                        "width": "100%",
                    },
                ),
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "0.4rem",
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
                    day: 'numeric',
                    month: 'long'
                });
                const hours = now.getHours().toString();
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
        def _render_presence(_n):
            # Purely a re-render of the latest background-scanned state;
            # does not itself trigger any ping/ARP network activity.
            return render_presence_badges(self.people)
