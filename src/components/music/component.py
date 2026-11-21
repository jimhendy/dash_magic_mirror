"""Now-playing tile with a one-tap "Pause all", via Home Assistant.

The tile is hidden while nothing is playing. After "Pause all" is tapped on
the dashboard, it stays up for `PAUSE_HOLD` showing what was paused, with a
"Resume" button - for pausing just while answering the door.

Optionally everything is paused automatically when the Header presence scan
sees the last person leave (`MUSIC_AUTO_PAUSE_WHEN_AWAY` in `app.config`);
that path doesn't hold the tile open, since nobody is there to resume.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from dash import Input, Output, dcc, html, no_update
from loguru import logger

from components.base import BaseComponent
from utils.data_repository import ComponentPayload, get_repository
from utils.ui import icon

from .data import (
    NowPlaying,
    fetch_active_players,
    group_now_playing,
    pause_players,
    play_players,
)

# Don't claim something is playing if HA hasn't answered for this long
STALE_AFTER = timedelta(seconds=30)
# How long the tile stays up (with "Resume") after Pause all is tapped here
PAUSE_HOLD = timedelta(minutes=5)
# After pausing/resuming, re-check HA up to this many times for it to agree
CONFIRM_ATTEMPTS = 6
CONFIRM_WAIT = 0.5


@dataclass(slots=True)
class MusicView:
    playing: list[NowPlaying] = field(default_factory=list)
    paused: list[NowPlaying] = field(default_factory=list)  # held after Pause all


@dataclass(slots=True)
class _Hold:
    rows: list[NowPlaying]
    until: datetime


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
        self._hold: _Hold | None = None
        self._hold_lock = threading.Lock()
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
    def _playing_rows(self) -> list[NowPlaying]:
        players = fetch_active_players(self.base_url, self.token, self.entity_ids)
        return group_now_playing(players)

    def _held_rows(self, playing: list[NowPlaying]) -> list[NowPlaying]:
        """Rows paused from the dashboard that are still within the hold window
        and haven't been resumed (here or anywhere else)."""
        playing_ids = {e for row in playing for e in row.entity_ids}
        with self._hold_lock:
            hold = self._hold
            if hold is None:
                return []
            if datetime.now(UTC) >= hold.until:
                self._hold = None
                return []
            rows = [r for r in hold.rows if not set(r.entity_ids) & playing_ids]
            if not rows:
                self._hold = None
            return rows

    def _compute_view(self) -> MusicView:
        playing = self._playing_rows()
        return MusicView(playing=playing, paused=self._held_rows(playing))

    async def _build_payload(self) -> ComponentPayload:
        view = await asyncio.to_thread(self._compute_view)
        return ComponentPayload(summary=None, raw=view)

    def pause_all(self, *, hold: bool = False) -> int:
        """Pause everything currently playing. Returns how many players.

        With `hold`, keep the tile up for PAUSE_HOLD so it can be resumed.
        """
        rows = self._playing_rows()
        entity_ids = [e for row in rows for e in row.entity_ids]
        pause_players(self.base_url, self.token, entity_ids)
        logger.info(f"Paused {len(entity_ids)} media player(s): {entity_ids}")
        if hold and rows:
            new_ids = set(entity_ids)
            with self._hold_lock:
                earlier = (
                    [r for r in self._hold.rows if not set(r.entity_ids) & new_ids]
                    if self._hold
                    else []
                )
                self._hold = _Hold(
                    rows=rows + earlier,
                    until=datetime.now(UTC) + PAUSE_HOLD,
                )
        return len(entity_ids)

    def resume_held(self) -> int:
        """Resume whatever Pause all paused (within the hold window)."""
        with self._hold_lock:
            rows = self._hold.rows if self._hold else []
        entity_ids = [e for row in rows for e in row.entity_ids]
        # Raises on failure, leaving the hold (and the Resume button) in place
        play_players(self.base_url, self.token, entity_ids)
        with self._hold_lock:
            self._hold = None
        logger.info(f"Resumed {len(entity_ids)} media player(s): {entity_ids}")
        return len(entity_ids)

    def pause_all_safe(self) -> None:
        """For automation hooks (everyone left): logs instead of raising."""
        try:
            self.pause_all()
        except Exception:  # noqa: BLE001
            logger.exception("Auto-pause via Home Assistant failed")

    def _view(self, payload: ComponentPayload | None) -> MusicView:
        if payload is None or not isinstance(payload.raw, MusicView):
            return MusicView()
        if datetime.now(UTC) - payload.updated_at > STALE_AFTER:
            return MusicView()
        return payload.raw

    # ---------------------------------------------------------------- render
    @staticmethod
    def _render_row(row: NowPlaying, *, paused: bool) -> html.Div:
        art = (
            html.Img(src=row.picture, className="music__art")
            if row.picture
            else html.Div(icon("mdi:music", "ic"), className="music__art is-empty")
        )
        parts = ["Paused"] if paused else []
        parts += [x for x in (row.artist, ", ".join(row.rooms)) if x]
        return html.Div(
            [
                art,
                html.Div(
                    [
                        html.Div(
                            row.title or "Playing", className="music__title truncate"
                        ),
                        html.Div(" · ".join(parts), className="music__meta truncate"),
                    ],
                    className="music__text",
                ),
            ],
            className="music__row" + (" is-paused" if paused else ""),
        )

    def _render(self, view: MusicView) -> tuple[list, str, str, str]:
        """rows, tile class, pause-button class, resume-button class."""
        rows = [self._render_row(r, paused=False) for r in view.playing] + [
            self._render_row(r, paused=True) for r in view.paused
        ]
        # `.is-active` shows the tile; dashboard.js then gives it a grid slot.
        tile = f"tile tile--{self.name}" + (" is-active" if rows else "")
        # Pause wins while anything is playing; otherwise offer Resume.
        show_pause = bool(view.playing) or not view.paused
        pause_cls = "music__btn music__btn--pause" + (
            "" if show_pause else " is-hidden"
        )
        resume_cls = "music__btn music__btn--resume" + (
            " is-hidden" if show_pause else ""
        )
        return rows, tile, pause_cls, resume_cls

    def _latest_payload(self) -> ComponentPayload | None:
        return self._repository.get_payload_snapshot(self._data_key)

    def tile_layout(self):
        tile = super().tile_layout()
        tile.className = self._render(self._view(self._latest_payload()))[1]
        return tile

    def _summary_layout(self):
        cid = self.component_id
        rows, _tile, pause_cls, resume_cls = self._render(
            self._view(self._latest_payload()),
        )
        return html.Div(
            [
                html.Div(rows, id=f"{cid}-rows", className="music__rows"),
                html.Div(
                    [
                        html.Button(
                            [icon("mdi:pause", "ic"), html.Span("Pause all")],
                            id=f"{cid}-pause-all",
                            n_clicks=0,
                            className=pause_cls,
                        ),
                        html.Button(
                            [icon("mdi:play", "ic"), html.Span("Resume")],
                            id=f"{cid}-resume",
                            n_clicks=0,
                            className=resume_cls,
                        ),
                    ],
                    className="music__actions",
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

        def outputs(allow_duplicate: bool = False):
            kw = {"allow_duplicate": True} if allow_duplicate else {}
            return [
                Output(f"{cid}-rows", "children", **kw),
                Output(cid, "className", **kw),
                Output(f"{cid}-pause-all", "className", **kw),
                Output(f"{cid}-resume", "className", **kw),
            ]

        def error(message: str):
            rows, tile, pause_cls, resume_cls = self._render(
                self._view(repo.get_payload_snapshot(data_key)),
            )
            return (
                [html.Div(message, className="music__error"), *rows],
                f"tile tile--{self.name} is-active",
                pause_cls,
                resume_cls,
            )

        async def refresh_until(done) -> tuple:
            # Wait briefly for HA to agree, so the tile doesn't flicker back.
            payload = None
            for _ in range(CONFIRM_ATTEMPTS):
                payload = await repo.refresh_now(data_key)
                if payload is not None and done(self._view(payload)):
                    break
                await asyncio.sleep(CONFIRM_WAIT)
            return self._render(self._view(payload))

        @app.callback(
            *outputs(),
            Input(f"{cid}-interval", "n_intervals"),
            prevent_initial_call=True,
        )
        async def hydrate_music(_n):
            return self._render(self._view(await repo.get_payload_async(data_key)))

        @app.callback(
            *outputs(allow_duplicate=True),
            Input(f"{cid}-pause-all", "n_clicks"),
            prevent_initial_call=True,
        )
        async def pause_all_clicked(n_clicks):
            if not n_clicks:
                return (no_update,) * 4
            try:
                await asyncio.to_thread(lambda: self.pause_all(hold=True))
            except Exception:  # noqa: BLE001
                logger.exception("Pause all via Home Assistant failed")
                return error("Couldn't pause – is Home Assistant up?")
            return await refresh_until(lambda v: not v.playing)

        @app.callback(
            *outputs(allow_duplicate=True),
            Input(f"{cid}-resume", "n_clicks"),
            prevent_initial_call=True,
        )
        async def resume_clicked(n_clicks):
            if not n_clicks:
                return (no_update,) * 4
            try:
                await asyncio.to_thread(self.resume_held)
            except Exception:  # noqa: BLE001
                logger.exception("Resume via Home Assistant failed")
                return error("Couldn't resume – is Home Assistant up?")
            return await refresh_until(lambda v: bool(v.playing))
