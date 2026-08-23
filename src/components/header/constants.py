"""Constants for the Header component (clock + presence)."""

# How often each connected browser tab re-renders the presence badges from
# the latest already-scanned state (no network I/O of its own).
PRESENCE_POLL_INTERVAL_MS: int = 60_000  # 1 minute
# How often the shared background repository actually scans the network
# (ping + ARP), regardless of how many browser tabs are open.
DEFAULT_PRESENCE_SCAN_INTERVAL_SECONDS: float = 30
DEFAULT_GRACE_SECONDS: int = 180
DEFAULT_ARP_TIMEOUT: int = 2
DEFAULT_PING_ATTEMPTS: int = 6
DEFAULT_PING_WAIT: float = 0.5

__all__ = [
    "DEFAULT_ARP_TIMEOUT",
    "DEFAULT_GRACE_SECONDS",
    "DEFAULT_PING_ATTEMPTS",
    "DEFAULT_PING_WAIT",
    "DEFAULT_PRESENCE_SCAN_INTERVAL_SECONDS",
    "PRESENCE_POLL_INTERVAL_MS",
]
