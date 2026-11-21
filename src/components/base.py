import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
from dash.development.base_component import Component

from utils.data_repository import LOADING_POLL_MS, ComponentPayload, get_repository
from utils.ui import icon, placeholder, updated_ago_label

_COMPONENT_COUNT = 0


class BaseComponent(ABC):
    """Base class for every dashboard component.

    A component renders two things:

    - a **tile** on the dashboard grid (`tile_layout`), and
    - optionally a full-screen **panel** with more detail (`panel_layout`).

    Panels are mounted once, hidden, alongside the dashboard - opening one
    is a pure client-side class toggle (`assets/dashboard.js`), not a Dash
    callback. That's what makes a single tap reliably open a panel straight
    away even on a slow tablet: there's nothing to round-trip or render at
    tap time, and a background refresh replacing a tile's contents mid-tap
    can't swallow the tap because the tap target (the tile frame) is never
    re-rendered.
    """

    title: str = ""
    icon: str = "mdi:circle-outline"
    # Optional accent for the tile's header icon (any CSS color).
    accent: str | None = None

    def __init__(
        self,
        name: str,
        *,
        full_screen: bool = True,
        grid_area: str | None = None,
    ):
        global _COMPONENT_COUNT
        self.name = name
        self._id = _COMPONENT_COUNT
        _COMPONENT_COUNT += 1
        self.full_screen = full_screen
        self.grid_area = grid_area or name

    @property
    def component_id(self) -> str:
        """Returns the unique ID for the component, used in Dash callbacks."""
        return f"{self.name}-{self._id}"

    @staticmethod
    def credentials_dir() -> Path:
        """Returns the directory where component credentials are stored."""
        dir = Path(__file__).parents[2] / "credentials"
        if not dir.exists():
            dir.mkdir(parents=True, exist_ok=True)
        return dir

    # ------------------------------------------------------------------
    # Tile
    # ------------------------------------------------------------------
    def tile_layout(self) -> Component:
        cid = self.component_id
        # No title bar - the contents say what each tile is. The badge slot
        # is only there for an occasional alert and collapses when empty.
        badge = html.Div(self._tile_badge(), id=f"{cid}-badge", className="tile__badge")
        attrs: dict[str, Any] = {"data-open": self.name} if self.full_screen else {}
        return html.Div(
            [
                badge,
                html.Div(
                    self._summary_layout(), id=f"{cid}-summary", className="tile__body"
                ),
                *self._hidden_layout(),
            ],
            id=cid,
            className=f"tile tile--{self.name}"
            + (" is-tappable" if self.full_screen else ""),
            style={"gridArea": self.grid_area},
            **attrs,
        )

    @abstractmethod
    def _summary_layout(self) -> Any:
        """Initial tile body."""

    def _tile_badge(self) -> Any:
        """Initial tile alert badge (optional)."""
        return None

    def _stamp(self, payload: ComponentPayload) -> str:
        stamp = payload.updated_at.isoformat()
        return f"too-old:{stamp}" if self._too_old(payload) else stamp

    def _hidden_layout(self) -> list[Component]:
        """Intervals / stores this component needs mounted with its tile."""
        return []

    # ------------------------------------------------------------------
    # Panel
    # ------------------------------------------------------------------
    refreshable: bool = False

    def panel_layout(self) -> Component:
        cid = self.component_id
        actions = []
        if self.refreshable:
            actions.append(
                html.Button(
                    icon("mdi:refresh", "ic"),
                    id=f"{cid}-refresh",
                    n_clicks=0,
                    className="icon-btn",
                    title="Refresh now",
                ),
            )
        actions.append(
            html.Div(
                html.Div(className="timer__ring"),
                className="timer",
                title="Returns home automatically",
                **{"data-timer": ""},
            ),
        )
        return html.Section(
            [
                html.Header(
                    [
                        html.Button(
                            [icon("mdi:chevron-left", "ic"), html.Span("Home")],
                            className="back-btn",
                            **{"data-close": ""},
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        icon(self.icon, "panel__icon"),
                                        html.H2(self.title, className="panel__title"),
                                    ],
                                    className="panel__title-row",
                                ),
                                html.Div(
                                    self._panel_subtitle(),
                                    id=f"{cid}-subtitle",
                                    className="panel__subtitle",
                                ),
                            ],
                            className="panel__titles",
                        ),
                        html.Div(actions, className="panel__actions"),
                    ],
                    className="panel__head",
                ),
                html.Div(
                    self._detail_layout(),
                    id=f"{cid}-detail",
                    className="panel__body",
                ),
            ],
            id=f"panel-{self.name}",
            className=f"panel panel--{self.name}",
            style={"--tile-accent": self.accent} if self.accent else None,
            **{"data-panel": self.name},
        )

    def _detail_layout(self) -> Any:
        return None

    def _panel_subtitle(self) -> Any:
        return None

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def add_callbacks(self, app: Dash) -> None:
        self._add_callbacks(app)

    @abstractmethod
    def _add_callbacks(self, app: Dash) -> None:
        """Register this component's callbacks."""


class DataDrivenComponent(BaseComponent, ABC):
    """Base for components backed by the shared `DataRepository`.

    Handles the boilerplate every fetch-driven component needs: registering
    a background refresher (with a warm sync fetch at startup so the first
    render isn't empty), reading the latest cached payload, the loading /
    error placeholder, and one hydrate callback that pushes the latest
    payload into the tile, the panel, and the panel subtitle/badge.
    Subclasses only implement `_build_payload()` and set `refresh_seconds`.

    The hydrate callback skips sending anything when the payload hasn't
    changed since this browser last received it (tracked per-client in a
    `dcc.Store`), so a slow tablet isn't made to diff identical component
    trees every interval.

    This is also the seam a future standalone caching API would slot into:
    everything here talks to `DataRepository` by key, never to a specific
    HTTP client or scraper directly.
    """

    refresh_seconds: float = 300
    jitter_seconds: float = 0
    placeholder_loading = "Loading..."
    placeholder_error = "Unavailable"
    refreshable = True
    # "updated X ago" appears (amber) once data is older than this; red at 3x.
    # None -> 3x refresh_seconds, at least 2 minutes.
    stale_after_seconds: float | None = None
    # If set, data older than this is replaced by `placeholder_error` (for data
    # that's misleading when old, e.g. departure times).
    max_age_seconds: float | None = None

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self._repository = get_repository()
        self._data_key = self.name
        try:
            self._repository.register_component(
                self._data_key,
                refresh_coro=self._build_payload,
                interval_seconds=self.refresh_seconds,
                jitter_seconds=self.jitter_seconds,
            )
            # The first fetch runs in the background repository loop, so startup
            # never blocks on (or hangs in) a network call; tiles show their
            # loading placeholder and poll quickly until data arrives.
            self._initial_payload = None
        except ValueError:
            # Already registered (e.g. hot reload) - reuse the existing snapshot.
            self._initial_payload = self._repository.get_payload_snapshot(
                self._data_key,
            )

    @abstractmethod
    async def _build_payload(self) -> ComponentPayload | None:
        """Fetch data and render it into a `ComponentPayload`."""

    def _build_placeholder(self, message: str) -> html.Div:
        return placeholder(message)

    def _latest_payload(self) -> ComponentPayload | None:
        return (
            self._repository.get_payload_snapshot(self._data_key)
            or self._initial_payload
        )

    def _summary_layout(self):
        payload = self._latest_payload()
        if payload and self._too_old(payload):
            return self._build_placeholder(self.placeholder_error)
        if payload and payload.summary is not None:
            return payload.summary
        return self._build_placeholder(self.placeholder_loading)

    def _detail_layout(self):
        payload = self._latest_payload()
        if payload and self._too_old(payload):
            return self._build_placeholder(self.placeholder_error)
        if payload and payload.detail is not None:
            return payload.detail
        return self._build_placeholder(self.placeholder_loading)

    def _panel_subtitle(self):
        payload = self._latest_payload()
        return payload.subtitle if payload else None

    def _tile_badge(self):
        payload = self._latest_payload()
        return payload.badge if payload else None

    def _poll_ms(self, payload: ComponentPayload | None) -> int:
        """Poll quickly until there's data, then at the refresh interval."""
        return int(self.refresh_seconds * 1000) if payload else LOADING_POLL_MS

    def _stale_after(self) -> float:
        if self.stale_after_seconds is not None:
            return self.stale_after_seconds
        return max(3 * self.refresh_seconds, 120)

    def _updated_label(self, payload: ComponentPayload | None) -> Any:
        if payload is None or payload.is_error:
            return None
        return updated_ago_label(payload.updated_at, self._stale_after())

    def _too_old(self, payload: ComponentPayload) -> bool:
        if self.max_age_seconds is None:
            return False
        age = (datetime.now(UTC) - payload.updated_at).total_seconds()
        return age > self.max_age_seconds

    def _hidden_layout(self) -> list[Component]:
        payload = self._latest_payload()
        return [
            html.Div(
                self._updated_label(payload),
                id=f"{self.component_id}-updated",
                className="tile__updated",
            ),
            dcc.Interval(
                id=f"{self.component_id}-interval",
                interval=self._poll_ms(payload),
                n_intervals=0,
            ),
            dcc.Store(
                id=f"{self.component_id}-stamp",
                data=self._stamp(payload) if payload else None,
            ),
        ]

    def _add_callbacks(self, app: Dash) -> None:
        repo = self._repository
        data_key = self._data_key
        cid = self.component_id

        @app.callback(
            Output(f"{cid}-summary", "children"),
            Output(f"{cid}-detail", "children"),
            Output(f"{cid}-subtitle", "children"),
            Output(f"{cid}-badge", "children"),
            Output(f"{cid}-stamp", "data"),
            Output(f"{cid}-updated", "children"),
            Output(f"{cid}-interval", "interval"),
            Input(f"{cid}-interval", "n_intervals"),
            Input(f"{cid}-refresh", "n_clicks"),
            State(f"{cid}-stamp", "data"),
            prevent_initial_call=True,
        )
        async def hydrate(_n, refresh_clicks, stamp):
            forced = ctx.triggered_id == f"{cid}-refresh" and refresh_clicks
            if forced:
                # Force-clear this component's file cache and refetch now.
                # (Imported here: utils.file_cache imports this module.)
                from utils.file_cache import clear_component_cache

                clear_component_cache(data_key)
                await asyncio.to_thread(repo.refresh_now_sync, data_key)

            payload = await repo.get_payload_async(data_key)
            if payload is None:
                payload = self._latest_payload()
            else:
                self._initial_payload = payload

            if payload is None:
                # Nothing fetched yet: keep the loading placeholder, poll fast.
                return (no_update,) * 6 + (LOADING_POLL_MS,)

            poll_ms = self._poll_ms(payload)
            new_stamp = payload.updated_at.isoformat()
            if self._too_old(payload):
                # Refreshes have been failing for a while; don't show old data.
                new_stamp = f"too-old:{new_stamp}"
                if new_stamp == stamp:
                    return (no_update,) * 6 + (poll_ms,)
                error = self._build_placeholder(self.placeholder_error)
                return (
                    error,
                    error,
                    no_update,
                    no_update,
                    new_stamp,
                    self._updated_label(payload),
                    poll_ms,
                )

            if new_stamp == stamp and not forced:
                return (no_update,) * 6 + (poll_ms,)
            return (
                payload.summary,
                payload.detail,
                payload.subtitle,
                payload.badge,
                new_stamp,
                self._updated_label(payload),
                poll_ms,
            )
