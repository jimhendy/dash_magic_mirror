"""Data + network helpers for Header component (presence + clock).

Migrated from the deprecated presence module.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Iterable
from dataclasses import dataclass

from loguru import logger
from scapy.all import ARP, Ether, srp  # type: ignore


@dataclass
class PersonPresence:
    name: str
    mac: str  # normalized
    ip: str
    is_home: bool = False
    # last_seen stored dynamically (not part of dataclass fields for clarity)


def _norm(mac: str) -> str:
    return mac.strip().strip('"').lower().replace("-", ":")


# Backwards compatibility alias
_norm_mac = _norm  # type: ignore


def ping_ip(ip: str, attempts: int = 5, wait: float = 0.5) -> bool:
    for _ in range(attempts):
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", ip],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(wait)
    return False


def get_mac_for_ip(ip: str, timeout: int) -> str | None:
    try:
        arp = ARP(pdst=ip)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp
        answered, _ = srp(packet, timeout=timeout, verbose=0)
        for _s, r in answered:
            return r.hwsrc.lower()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"ARP lookup failed for {ip}: {e}")
    return None


def update_people_presence_by_ip(
    people: Iterable[PersonPresence],
    now: float,
    grace_seconds: int,
    arp_timeout: int,
    ping_attempts: int,
    ping_wait: float,
):
    for person in people:
        expected_mac = person.mac
        ip = person.ip
        present = False
        ping_ip(ip, attempts=ping_attempts, wait=ping_wait)
        mac = get_mac_for_ip(ip, timeout=arp_timeout)
        if mac:
            if mac == expected_mac:
                present = True
            else:
                logger.warning(
                    f"Presence MAC mismatch for {person.name} ip={ip}: got {mac} expected {expected_mac}",
                )
        if present:
            person.is_home = True
            person.last_seen = now  # type: ignore[attr-defined]
        else:
            last_seen = getattr(person, "last_seen", 0)
            person.is_home = (now - last_seen) <= grace_seconds
        logger.debug(
            f"Presence update name={person.name} ip={ip} expected_mac={expected_mac} present={person.is_home}",
        )


__all__ = [
    "PersonPresence",
    "_norm",
    "_norm_mac",
    "get_mac_for_ip",
    "ping_ip",
    "update_people_presence_by_ip",
]
