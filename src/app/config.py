import os
from pathlib import Path

from dotenv import load_dotenv

from components.google_calendar import GoogleCalendar
from components.header import Header
from components.header.component import PersonPresence, _norm
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
TFL_PRIMARY_STOP_ID = os.environ.get("TFL_STOP_ID_1", "")
TFL_ALL_STOP_IDS = [
    os.environ[stop_id]
    for stop_id in os.environ
    if stop_id.startswith("TFL_STOP_ID_") and os.environ.get(stop_id)
]
TFL_TRANSFER_STATION_ID = os.environ.get("TFL_TRANSFER_STATION_ID", "")
TFL_SUMMARY_IGNORE_DESTINATION = os.environ.get("TFL_SUMMARY_IGNORE_DESTINATION", "")

# Component instances
COMPONENTS = [
    Header(
        people=people,
        grace_seconds=PRESENCE_GRACE_SECONDS,
        arp_timeout=PRESENCE_ARP_TIMEOUT,
        ping_attempts=PRESENCE_PING_ATTEMPTS,
        ping_wait=PRESENCE_PING_WAIT,
    ),
    Weather(
        postcode=os.environ.get("WEATHER_POSTCODE", "SW1A 1AA"),
        api_key=os.environ.get("WEATHER_API_KEY", ""),
    ),
    GoogleCalendar(
        calendar_ids=[
            os.environ[calendar_id]
            for calendar_id in os.environ
            if calendar_id.startswith("GOOGLE_CALENDAR_ID_")
        ],
    ),
    TFLArrivals(
        primary_stop_id=TFL_PRIMARY_STOP_ID,
        all_stop_ids=TFL_ALL_STOP_IDS,
        transfer_station_id=TFL_TRANSFER_STATION_ID,
        summary_ignore_destination=TFL_SUMMARY_IGNORE_DESTINATION,
    ),
    Sports(),
]
