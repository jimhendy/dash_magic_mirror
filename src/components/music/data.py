"""Home Assistant media_player access for the Music tile.

Uses the HA REST API with a long-lived access token:
  GET  /api/states                              -> media_player entities
  POST /api/services/media_player/media_pause   -> pause entities
  POST /api/services/media_player/media_play    -> resume entities

Music Assistant players appear in HA as media_player entities, so this covers
them as well as any other speakers or TVs HA knows about.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

HTTP_TIMEOUT = 5.0
# States that mean "making noise right now"
ACTIVE_STATES = frozenset({"playing", "buffering"})


@dataclass(frozen=True, slots=True)
class PlayerState:
    entity_id: str
    name: str
    title: str
    artist: str
    picture: str | None  # absolute URL, loaded by the tablet directly from HA


@dataclass(frozen=True, slots=True)
class NowPlaying:
    """One row in the tile: a track playing in one or more rooms."""

    rooms: tuple[str, ...]
    entity_ids: tuple[str, ...]
    title: str
    artist: str
    picture: str | None


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def fetch_active_players(
    base_url: str,
    token: str,
    entity_ids: list[str] | None = None,
) -> list[PlayerState]:
    """Media players that are currently playing. Raises on HTTP failure."""
    resp = httpx.get(
        f"{base_url}/api/states",
        headers=_headers(token),
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    wanted = set(entity_ids or [])

    players: list[PlayerState] = []
    for entity in resp.json():
        entity_id = entity.get("entity_id", "")
        if not entity_id.startswith("media_player."):
            continue
        if wanted and entity_id not in wanted:
            continue
        if entity.get("state") not in ACTIVE_STATES:
            continue
        attrs = entity.get("attributes", {})
        picture = attrs.get("entity_picture")
        if picture and picture.startswith("/"):
            picture = f"{base_url}{picture}"
        players.append(
            PlayerState(
                entity_id=entity_id,
                name=attrs.get("friendly_name") or entity_id.split(".", 1)[1],
                title=attrs.get("media_title") or "",
                artist=attrs.get("media_artist") or attrs.get("app_name") or "",
                picture=picture,
            ),
        )
    return players


def group_now_playing(players: list[PlayerState]) -> list[NowPlaying]:
    """Collapse players showing the same track into one row.

    Grouped speakers, and the same speaker exposed twice (a Music Assistant
    player plus the native Cast/Sonos entity), report identical metadata, so
    they appear once with the rooms listed together.
    """
    groups: dict[tuple[str, str] | str, list[PlayerState]] = {}
    for p in players:
        key: tuple[str, str] | str = (
            (p.title, p.artist) if (p.title or p.artist) else p.entity_id
        )
        groups.setdefault(key, []).append(p)

    return [
        NowPlaying(
            rooms=tuple(dict.fromkeys(m.name for m in members)),
            entity_ids=tuple(m.entity_id for m in members),
            title=members[0].title,
            artist=members[0].artist,
            picture=next((m.picture for m in members if m.picture), None),
        )
        for members in groups.values()
    ]


def _call_service(
    base_url: str, token: str, service: str, entity_ids: list[str]
) -> None:
    if not entity_ids:
        return
    resp = httpx.post(
        f"{base_url}/api/services/media_player/{service}",
        headers=_headers(token),
        json={"entity_id": entity_ids},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()


def pause_players(base_url: str, token: str, entity_ids: list[str]) -> None:
    """Pause the given media players. Raises on HTTP failure."""
    _call_service(base_url, token, "media_pause", entity_ids)


def play_players(base_url: str, token: str, entity_ids: list[str]) -> None:
    """Resume the given media players. Raises on HTTP failure."""
    _call_service(base_url, token, "media_play", entity_ids)
