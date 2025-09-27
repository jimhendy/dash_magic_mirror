from __future__ import annotations

import asyncio
import random
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger


@dataclass(slots=True)
class ComponentPayload:
    """Snapshot of component data ready to hydrate the UI."""

    summary: Any
    fullscreen_title: Any | None = None
    fullscreen_content: Any | None = None
    raw: Any | None = None
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


@dataclass(slots=True)
class _Refresher:
    key: str
    factory: Callable[[], Awaitable[ComponentPayload | None]]
    interval: float
    jitter: float = 0.0


class DataRepository:
    """Central cache for component payloads with background refresh support."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._payloads: dict[str, ComponentPayload] = {}
        self._refreshers: dict[str, _Refresher] = {}
        self._runner: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started = False
        self._start_lock = threading.Lock()
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Registration & warm-up
    # ------------------------------------------------------------------
    def register_component(
        self,
        key: str,
        *,
        refresh_coro: Callable[[], Awaitable[ComponentPayload | None]],
        interval_seconds: float,
        jitter_seconds: float = 0.0,
    ) -> None:
        if interval_seconds <= 0:
            msg = f"Interval must be positive for refresher '{key}'"
            raise ValueError(msg)

        with self._lock:
            if key in self._refreshers:
                msg = f"Refresher already registered for '{key}'"
                raise ValueError(msg)
            self._refreshers[key] = _Refresher(
                key=key,
                factory=refresh_coro,
                interval=interval_seconds,
                jitter=jitter_seconds,
            )

    def refresh_now_sync(self, key: str) -> ComponentPayload | None:
        """Synchronously invoke the refresher for a component."""
        refresher = self._refreshers.get(key)
        if refresher is None:
            msg = f"No refresher registered for '{key}'"
            raise KeyError(msg)

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._execute_refresh(refresher))
        finally:
            loop.close()

    # ------------------------------------------------------------------
    # Payload accessors
    # ------------------------------------------------------------------
    def get_payload_snapshot(self, key: str) -> ComponentPayload | None:
        with self._lock:
            return self._payloads.get(key)

    async def get_payload_async(self, key: str) -> ComponentPayload | None:
        return await asyncio.to_thread(self.get_payload_snapshot, key)

    # ------------------------------------------------------------------
    # Background runner lifecycle
    # ------------------------------------------------------------------
    def ensure_started(self) -> None:
        with self._start_lock:
            if self._started:
                return
            self._started = True
            self._stop_event.clear()
            self._runner = threading.Thread(
                target=self._run_loop,
                name="data-repository-refresh",
                daemon=True,
            )
            self._runner.start()

    def stop(self) -> None:
        with self._start_lock:
            if not self._started:
                return
            self._stop_event.set()
            if self._loop is not None:
                self._loop.call_soon_threadsafe(lambda: None)
            if self._runner is not None:
                self._runner.join(timeout=2)
            self._started = False
            self._runner = None
            self._loop = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            tasks = [
                self._loop.create_task(self._refresh_loop(refresher))
                for refresher in self._refreshers.values()
            ]
            if tasks:
                self._loop.run_until_complete(asyncio.gather(*tasks))
            else:
                # Nothing registered yet; wait until stop signal arrives
                self._loop.run_until_complete(self._idle_until_stopped())
        except Exception:  # noqa: BLE001 - log unexpected loop failure
            logger.exception("Data repository background loop crashed")
        finally:
            if self._loop and not self._loop.is_closed():
                self._loop.close()

    async def _idle_until_stopped(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(0.5)

    async def _refresh_loop(self, refresher: _Refresher) -> None:
        # Run once immediately to keep data warm
        await self._execute_refresh(refresher)
        while not self._stop_event.is_set():
            sleep_for = refresher.interval
            if refresher.jitter:
                jitter = random.uniform(-refresher.jitter, refresher.jitter)
                sleep_for = max(1.0, refresher.interval + jitter)
            await self._sleep_with_stop(sleep_for)
            if self._stop_event.is_set():
                break
            await self._execute_refresh(refresher)

    async def _sleep_with_stop(self, duration: float) -> None:
        end = time.monotonic() + duration
        while not self._stop_event.is_set():
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            await asyncio.sleep(min(remaining, 1.0))

    async def _execute_refresh(self, refresher: _Refresher) -> ComponentPayload | None:
        try:
            payload = await refresher.factory()
        except Exception:  # noqa: BLE001 - log & retain previous payload
            logger.exception("Refresher '%s' failed", refresher.key)
            return None
        if payload is None:
            logger.warning("Refresher '%s' returned no payload", refresher.key)
            return None
        if payload.updated_at is None:
            payload.updated_at = datetime.now(UTC)
        with self._lock:
            self._payloads[refresher.key] = payload
        return payload


_repository: DataRepository | None = None
_repository_lock = threading.Lock()


def get_repository() -> DataRepository:
    global _repository
    if _repository is None:
        with _repository_lock:
            if _repository is None:
                _repository = DataRepository()
    return _repository
