import os
from pathlib import Path

from dotenv import load_dotenv

from components.google_calendar import GoogleCalendar
from components.header import Header
from components.header.component import PersonPresence, _norm
from components.markets import Markets
from components.music import Music
from components.sports import Sports
from components.tfl_arrivals import TFLArrivals
from components.weather import Weather

env_path = Path(__file__).parents[2] / ".env"
load_dotenv(env_path)

# Presence configuration extracted from environment (paired IP + MAC)
PRESENCE_GRACE_SECONDS = int(os.environ.get("MAGIC_MIRROR_PRESENCE_GRACE", "180"))
PRESENCE_ARP_TIMEOUT = int(os.environ.get("MAGIC_MIRROR_PRESENCE_ARP_TIMEOUT", "2"))
PRESENCE_PING_ATTEMPTS = int(os.environ.get("MAGIC_MIRROR_PRESENCE_PING_ATTEMPTS", "6"))
PRESENCE_PING_WAIT = float(os.environ.get("MAGIC_MIRROR_PRESENCE_PING_WAIT", "0.5"))

people: list[PersonPresence] = []
ips: dict[str, str] = {}
macs: dict[str, str] = {}
for k, v in os.environ.items():
    if k.startswith("MAGIC_MIRROR_PRESENCE_IP_"):
        name = k[len("MAGIC_MIRROR_PRESENCE_IP_") :].upper()
        ips[name] = v.strip()
    elif k.startswith("MAGIC_MIRROR_PRESENCE_MAC_"):
        name = k[len("MAGIC_MIRROR_PRESENCE_MAC_") :].upper()
        macs[name] = _norm(v)

# Validate pairing
all_keys = set(ips) | set(macs)
errors: list[str] = []
for key in all_keys:
    if key not in ips:
        errors.append(f"Missing IP for {key} (have MAC)")
    if key not in macs:
        errors.append(f"Missing MAC for {key} (have IP)")
if errors:
    raise RuntimeError("Presence configuration errors: " + "; ".join(errors))

for key in sorted(all_keys):
    raw_name = key.title().replace("_", " ")
    people.append(PersonPresence(name=raw_name, mac=macs[key], ip=ips[key]))

# TFL configuration
TFL_ALL_STOP_IDS = [
    os.environ[stop_id]
    for stop_id in os.environ
    if stop_id.startswith("TFL_STOP_ID_") and os.environ.get(stop_id)
]
TFL_SUMMARY_IGNORE_DESTINATION = os.environ.get("TFL_SUMMARY_IGNORE_DESTINATION", "")
TFL_LINE_STATUS_IDS = [
    value.strip()
    for value in os.environ.get("TFL_LINE_STATUS", "").split(",")
    if value.strip()
]

# Component instances.
#
# Where each one sits is decided by its `grid_area` (defaults to the
# component's name) and the portrait/landscape `grid-template-areas` in
# assets/main.css - not by the order here. The order only decides the
# order of the detail panels in the DOM.
HEADER = Header(
    people=people,
    grace_seconds=PRESENCE_GRACE_SECONDS,
    arp_timeout=PRESENCE_ARP_TIMEOUT,
    ping_attempts=PRESENCE_PING_ATTEMPTS,
    ping_wait=PRESENCE_PING_WAIT,
)

# Home Assistant "now playing" tile (only when a token is configured)
HOME_ASSISTANT_URL = os.environ.get("HOME_ASSISTANT_URL", "").strip()
HOME_ASSISTANT_TOKEN = os.environ.get("HOME_ASSISTANT_TOKEN", "").strip()
MUSIC_PLAYER_ENTITIES = [
    value.strip()
    for value in os.environ.get("MUSIC_PLAYER_ENTITIES", "").split(",")
    if value.strip()
]
MUSIC_AUTO_PAUSE_WHEN_AWAY = os.environ.get(
    "MUSIC_AUTO_PAUSE_WHEN_AWAY", ""
).strip().lower() in {"1", "true", "yes", "on"}

MUSIC = (
    Music(
        base_url=HOME_ASSISTANT_URL,
        token=HOME_ASSISTANT_TOKEN,
        entity_ids=MUSIC_PLAYER_ENTITIES,
    )
    if HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN
    else None
)
if MUSIC and MUSIC_AUTO_PAUSE_WHEN_AWAY:
    HEADER.on_everyone_left = MUSIC.pause_all_safe

COMPONENTS = [
    HEADER,
    Weather(
        postcode=os.environ.get("WEATHER_POSTCODE", "SW1A 1AA"),
        api_key=os.environ.get("WEATHER_API_KEY", ""),
    ),
    TFLArrivals(
        all_stop_ids=TFL_ALL_STOP_IDS,
        summary_ignore_destination=TFL_SUMMARY_IGNORE_DESTINATION,
        line_status_ids=TFL_LINE_STATUS_IDS,
    ),
    GoogleCalendar(
        calendar_ids=[
            os.environ[calendar_id]
            for calendar_id in sorted(os.environ)
            if calendar_id.startswith("GOOGLE_CALENDAR_ID_")
        ],
    ),
    Sports(),
    Markets(),
    *([MUSIC] if MUSIC else []),
]
