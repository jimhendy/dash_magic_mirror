# Magic Mirror Dashboard

A dark-glass magic mirror dashboard built with Dash and Python, running on a Raspberry Pi 4 and viewed on an old Android tablet mounted by the front door. Real-time London transport arrivals, weather, calendar events, sports fixtures, and news headlines, all in one always-on display.

## Architecture

Every component follows the same shape:

```
components/<name>/
  __init__.py      # exports the component class
  component.py     # Dash wiring: registers with the DataRepository, hydrate callback
  constants.py      # cache lifetimes, timeouts, etc.
  data.py           # fetch + parse external data (the only place that talks to a network/API)
  summary.py        # the compact single-line card shown in the always-on strip
  full_screen.py    # the detailed view shown when a card is tapped
```

Two shared pieces do most of the heavy lifting:

- **`utils.data_repository.DataRepository`** (`src/utils/data_repository.py`) - a single background asyncio loop that polls each component's `data.py` on its own cadence (with jitter, so components don't all hit the network at once) and caches the rendered result in memory. Every browser tab reads from this shared cache instead of triggering its own fetch, so opening the dashboard on a second device never doubles API traffic.
- **`components.base.DataDrivenComponent`** (`src/components/base.py`) - the base class every fetch-driven component subclasses. It owns registering with the `DataRepository`, the loading/error placeholder, and the hydrate callback that pushes the latest cached payload into the page. A concrete component only implements `_build_payload()` (fetch data, render it) - everything else (the interval, the full-screen preload stores, the callback wiring) is inherited.

This split is deliberate: `data.py` never touches the Dash layer, and `component.py`/`summary.py`/`full_screen.py` never talk to the network directly - they only ever read from the repository. If this ever moves to a Home Assistant setup where fetching/caching lives in a standalone service, only `DataRepository`'s internals need to change (in-process background loop -> HTTP client against that service); no component code would need to move.

On top of `DataRepository`, the file-based `@cache_json` decorator (`src/utils/file_cache.py`) is still what actually rate-limits each external API call - see [Component Development & Rate Limiting](#component-development--rate-limiting) below.

### Presence detection

Presence (`components/header`) is a bit different: it scans the LAN (ping + targeted ARP) rather than calling an external API, but it follows the same "one shared background scan, not one per browser tab" principle via `DataRepository` - the scan runs on its own interval in the background, and each connected client's clock/presence poll just re-renders the latest already-scanned state instead of triggering new network I/O.

Detection flow, per configured person:
1. (Optional wake) ICMP ping attempts per configured IP
2. Targeted ARP request for that IP
3. MAC match validation (with a warning on mismatch)
4. Grace-window debouncing (a device is considered "home" until the grace period expires after its last positive sighting)

### Design system

The whole UI is built from one token module, `src/utils/styles.py`, in an editorial "quiet luxury" style rather than a boxed dashboard-template look: individual rows (a calendar event, a bus arrival, a fixture) are plain text on the near-black background, not wrapped in bordered/shadowed cards - the one thing that most reads as "generated from a UI kit". Each section instead opens with a small muted uppercase "kicker" label (`kicker_style()`), color-codes at most with a thin left accent bar (`row_style(accent=...)`), and hero numerals (the clock, the current temperature) use a very light font weight (`hero_style()`) contrasted against small bold labels to carry the hierarchy instead of boxes. One accent color is used consistently for "now / today / live" states; red is reserved only for genuinely time-critical states (an arrival under 2 minutes, a service disruption). No `backdrop-filter` blur and minimal shadow anywhere, so it stays cheap to render on the Pi 4/tablet GPU. The Inter typeface is loaded via Google Fonts in `app/main.py`'s `index_string`. Top-level page rhythm comes from a single `gap` on the outer flex container (`app/core_layout.py`), not per-component separator elements, so spacing stays consistent regardless of how much each component renders.

## Setup

### Local Development

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure your locations:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and update the TFL stop IDs with your local transport stops. You can find stop IDs using the [TFL API](https://api.tfl.gov.uk/).

3. **Run the application:**
   ```bash
   just run
   ```
   
   Or directly with:
   ```bash
   cd src && uv run python -m app.main
   ```

### Docker Deployment

1. **Configure your environment:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your TFL stop IDs and other configuration.

2. **Build and run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```
   
   The application will be available at http://localhost:8050

3. **View logs:**
   ```bash
   docker-compose logs -f magic-mirror
   ```

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

**Note:** The Docker setup includes:
- Automatic restart on failure
- Persistent cache storage
- Health checks (curl is installed in the image specifically for this)
- Read-only mounting of configuration files

## Configuration

The application uses environment variables and `src/app/config.py` for configuration.

### Presence Configuration (Header Component)

Presence devices require paired IP + MAC environment variables. For a person named `Alice`:
```
MAGIC_MIRROR_PRESENCE_IP_ALICE=192.168.1.42
MAGIC_MIRROR_PRESENCE_MAC_ALICE=AA:BB:CC:DD:EE:FF
```
All names are uppercased when pairing; MACs are normalized automatically (case-insensitive, hyphens converted to colons). A configuration error is raised if any IP lacks a matching MAC (or vice versa).

Tuning parameters (all optional, with defaults shown):
```
MAGIC_MIRROR_PRESENCE_GRACE=180           # seconds to keep a device 'home' after last sighting
MAGIC_MIRROR_PRESENCE_ARP_TIMEOUT=2       # per targeted ARP request timeout (seconds)
MAGIC_MIRROR_PRESENCE_PING_ATTEMPTS=6     # ICMP attempts before ARP
MAGIC_MIRROR_PRESENCE_PING_WAIT=0.5       # delay between ping attempts
```

Grant raw socket capability (needed for ARP) to your Python binary if running outside Docker:
```sh
sudo setcap cap_net_raw,cap_net_admin=eip "$(readlink -f "$(uv run which python)")"
```

### Environment Variables

Copy `.env.example` to `.env` and customize:

- **Presence**: Paired IP/MAC variables as described above
- **TFL Stops**: Configure transport stop IDs and display names
- **TFL Line Status**: Optional comma-separated list (e.g. `metropolitan,circle`) to force status indicators when arrivals are missing
- **Weather**: Set your postcode and WeatherAPI key
- **Google Calendar**: Configure calendar IDs
- **News**: Optional `NEWS_RSS_URLS` (comma-separated) - defaults to BBC World + Guardian World, no key required
- **Tasks**: Optional `MAGIC_MIRROR_TASKS_FILE` to override where people/tasks are persisted (defaults to `~/.local/state/magic_mirror/tasks.json`)

## Features

- **Header (Clock + Presence)** - Unified time + household presence badges
- **Weather** - Current conditions and multi-day forecast (WeatherAPI.com), plus an hourly temperature/rain-chance chart in the full-screen view
- **Google Calendar** - Upcoming events across multiple calendars, with smart date formatting and birthday detection
- **TFL Transport** - Real-time London public transport arrivals, line status, and disruptions
- **Tasks** - Household people, one-off chores, and recurring chores with overdue highlighting
- **Sports Fixtures** - Upcoming matches across configured teams/sports, scraped from Where's The Match
- **News** - Rotating headlines from an RSS feed (default BBC News), full list in the full-screen view

Tap any card to open its full-screen view; it auto-closes after a countdown (reset by touch/mouse activity), or use the Back button. The trash-can icon in the full-screen nav bar force-clears that component's cache and refetches immediately.

## Component Development & Rate Limiting

### Cache JSON Decorator

The `@cache_json` decorator in `src/utils/file_cache.py` provides file-based caching for component data-fetching functions. This decorator is **essential** for implementing rate limiting and preventing excessive API calls - it's the actual thing standing between this app and an API ban, independent of the in-memory `DataRepository` caching layer described above.

#### Usage

```python
from src.utils.file_cache import cache_json
import datetime

@cache_json(valid_lifetime=datetime.timedelta(hours=1))
def fetch(self) -> dict:
    """Fetch data from external API."""
    # Your API call logic here
    return data
```

#### How It Works

1. **Cache Key Generation**: Creates a unique cache key based on function name and arguments using MD5 hash
2. **File-based Storage**: Stores cached results as JSON files in `~/.cache/magic_mirror/`
3. **Time-based Validation**: Returns cached data if within the `valid_lifetime` window
4. **Automatic Cleanup**: Removes expired cache files when generating new ones
5. **Fresh Data**: Only calls the decorated function when cache is invalid or missing

#### Rate Limiting Examples

Different components use appropriate cache lifetimes based on data update frequency:

- **TFL Arrivals**: `30 seconds` - Real-time transport data changes frequently
- **Weather**: `15 minutes` - Weather conditions update periodically
- **Google Calendar**: `5 minutes` refresh cadence in `DataRepository` (the calendar API call itself isn't separately `@cache_json`-wrapped)
- **Sports**: `36 hours` for the underlying HTML fetch - match schedules are relatively static
- **News**: `20 minutes` - RSS headlines update periodically, no API key/quota to worry about

### **CRITICAL: Component Rate Limiting Requirements**

⚠️ **Component developers MUST implement proper rate limiting** ⚠️

Without it, every browser tab or dev restart could trigger its own fetch cycle against an external API, risking quota exhaustion or a temporary ban. Two layers protect against this here:

1. `DataRepository` ensures only one background loop per component fetches data, no matter how many browser tabs are open.
2. `@cache_json` on the actual network-calling function in `data.py` ensures that even a fresh fetch cycle (e.g. app restart) reuses a still-valid cached response instead of hitting the API again.

New components should register with `DataRepository` (by subclassing `DataDrivenComponent`) **and** wrap their actual HTTP-calling function with `@cache_json(valid_lifetime=...)`, choosing a lifetime appropriate to how often the underlying data actually changes.

### Design Flaws & Considerations

The `cache_json` decorator provides effective rate limiting, but it's a simple file-based cache, not a production caching system:

1. **File system race conditions** - concurrent writes from multiple processes could rarely corrupt a cache file (mitigated: corrupt files are detected and refetched).
2. **No external invalidation** - stale data persists until the cache naturally expires; use the full-screen modal's cache-clear button, or a shorter lifetime, if that matters for a given component.
3. **No automatic cleanup** of old cache files - `magic-mirror-cache/`/`~/.cache/magic_mirror/` will grow slowly over time.
4. **Argument hashing** is based on the string representation of arguments (MD5) - fine for simple hashable arguments, not guaranteed stable for complex objects.
