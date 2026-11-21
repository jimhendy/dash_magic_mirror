"""Now-playing tile with a one-tap "Pause all", via Home Assistant.

The tile is hidden while nothing is playing. Optionally everything is paused
automatically when the Header presence scan sees the last person leave (see
`MUSIC_AUTO_PAUSE_WHEN_AWAY` in `app.config`).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from dash import Input, Output, dcc, html, no_update
from loguru import logger

from components.base import BaseComponent
from utils.data_repository import ComponentPayload, get_repository
from utils.ui import icon

from .data import NowPlaying, fetch_active_players, group_now_playing, pause_players

# Don't claim something is playing if HA hasn't answered for this long
STALE_AFTER = timedelta(seconds=30)
# After pausing, re-check HA up to this many times for it to report paused
PAUSE_CONFIRM_ATTEMPTS = 6
PAUSE_CONFIRM_WAIT = 0.5


class Music(BaseComponent):
    title = "Music"
    icon = "mdi:music"

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        entity_ids: list[str] | None = None,
        refresh_seconds: int = 5,
        **kwargs,
    ):
        super().__init__(name="music", full_screen=False, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.entity_ids = entity_ids or []
        self.refresh_seconds = refresh_seconds
        self._repository = get_repository()
        self._data_key = self.name
        try:
            self._repository.register_component(
                self._data_key,
                refresh_coro=self._build_payload,
                interval_seconds=self.refresh_seconds,
            )
        except ValueError:
            pass  # already registered (hot reload)

    # ------------------------------------------------------------------ data
    def _now_playing(self) -> list[NowPlaying]:
        players = fetch_active_players(self.base_url, self.token, self.entity_ids)
        return group_now_playing(players)

    async def _build_payload(self) -> ComponentPayload:
        rows = await asyncio.to_thread(self._now_playing)
        return ComponentPayload(summary=None, raw=rows)

    def pause_all(self) -> int:
        """Pause everything currently playing. Returns how many players."""
        players = fetch_active_players(self.base_url, self.token, self.entity_ids)
        entity_ids = [p.entity_id for p in players]
        pause_players(self.base_url, self.token, entity_ids)
        logger.info(f"Paused {len(entity_ids)} media player(s): {entity_ids}")
        return len(entity_ids)

    def pause_all_safe(self) -> None:
        """For automation hooks: logs instead of raising."""
        try:
            self.pause_all()
        except Exception:  # noqa: BLE001
            logger.exception("Auto-pause via Home Assistant failed")

    def _rows(self, payload: ComponentPayload | None) -> list[NowPlaying]:
        if payload is None or not payload.raw:
            return []
        if datetime.now(UTC) - payload.updated_at > STALE_AFTER:
            return []
        return payload.raw

    # ---------------------------------------------------------------- render
    def _tile_class(self, playing: bool) -> str:
        # `.is-playing` shows the tile and gives it a grid slot (assets/main.css)
        return f"tile tile--{self.name}" + (" is-playing" if playing else "")

    @staticmethod
    def _render_row(row: NowPlaying) -> html.Div:
        art = (
            html.Img(src=row.picture, className="music__art")
            if row.picture
            else html.Div(icon("mdi:music", "ic"), className="music__art is-empty")
        )
        meta = " · ".join(x for x in (row.artist, ", ".join(row.rooms)) if x)
        return html.Div(
            [
                art,
                html.Div(
                    [
                        html.Div(
                            row.title or "Playing", className="music__title truncate"
                        ),
                        html.Div(meta, className="music__meta truncate"),
                    ],
                    className="music__text",
                ),
            ],
            className="music__row",
        )

    def _render_rows(self, rows: list[NowPlaying]) -> list:
        return [self._render_row(r) for r in rows]

    def tile_layout(self):
        tile = super().tile_layout()
        tile.className = self._tile_class(bool(self._rows(self._latest_payload())))
        return tile

    def _latest_payload(self) -> ComponentPayload | None:
        return self._repository.get_payload_snapshot(self._data_key)

    def _summary_layout(self):
        cid = self.component_id
        return html.Div(
            [
                html.Div(
                    self._render_rows(self._rows(self._latest_payload())),
                    id=f"{cid}-rows",
                    className="music__rows",
                ),
                html.Button(
                    [icon("mdi:pause", "ic"), html.Span("Pause all")],
                    id=f"{cid}-pause-all",
                    n_clicks=0,
                    className="music__pause",
                ),
            ],
            className="music",
        )

    def _hidden_layout(self):
        return [
            dcc.Interval(
                id=f"{self.component_id}-interval",
                interval=self.refresh_seconds * 1000,
                n_intervals=0,
            ),
        ]

    # ------------------------------------------------------------- callbacks
    def _add_callbacks(self, app):
        repo = self._repository
        data_key = self._data_key
        cid = self.component_id

        def _view(payload: ComponentPayload | None):
            rows = self._rows(payload)
            return self._render_rows(rows), self._tile_class(bool(rows))

        @app.callback(
            Output(f"{cid}-rows", "children"),
            Output(cid, "className"),
            Input(f"{cid}-interval", "n_intervals"),
            prevent_initial_call=True,
        )
        async def hydrate_music(_n):
            return _view(await repo.get_payload_async(data_key))

        @app.callback(
            Output(f"{cid}-rows", "children", allow_duplicate=True),
            Output(cid, "className", allow_duplicate=True),
            Input(f"{cid}-pause-all", "n_clicks"),
            prevent_initial_call=True,
        )
        async def pause_all_clicked(n_clicks):
            if not n_clicks:
                return no_update, no_update
            try:
                await asyncio.to_thread(self.pause_all)
            except Exception:  # noqa: BLE001
                logger.exception("Pause all via Home Assistant failed")
                return [
                    html.Div(
                        "Couldn't pause – is Home Assistant up?",
                        className="music__error",
                    ),
                ], self._tile_class(True)
            # Wait briefly for HA to report the players as paused, so the tile
            # doesn't flicker back on the next poll.
            payload = None
            for _ in range(PAUSE_CONFIRM_ATTEMPTS):
                payload = await repo.refresh_now(data_key)
                if payload is not None and not payload.raw:
                    break
                await asyncio.sleep(PAUSE_CONFIRM_WAIT)
            return _view(payload)
