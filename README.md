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
  summary.py        # the dashboard tile's contents (and its header badge)
  full_screen.py    # the detail panel shown when the tile is tapped
```

Two shared pieces do most of the heavy lifting:

- **`utils.data_repository.DataRepository`** (`src/utils/data_repository.py`) - a single background asyncio loop that polls each component's `data.py` on its own cadence (with jitter, so components don't all hit the network at once) and caches the rendered result in memory. Every browser tab reads from this shared cache instead of triggering its own fetch, so opening the dashboard on a second device never doubles API traffic.
- **`components.base.DataDrivenComponent`** (`src/components/base.py`) - the base class every fetch-driven component subclasses. It owns registering with the `DataRepository`, the loading/error placeholder, the tile and panel chrome, and one hydrate callback that pushes the latest cached `ComponentPayload` (`summary`, `detail`, `subtitle`, `badge`) into the page - skipping the update entirely when nothing changed since that browser last received it. A concrete component only implements `_build_payload()` (fetch data, render it) and sets `title`/`icon`/`accent`; everything else is inherited.

This split is deliberate: `data.py` never touches the Dash layer, and `component.py`/`summary.py`/`full_screen.py` never talk to the network directly - they only ever read from the repository. If this ever moves to a Home Assistant setup where fetching/caching lives in a standalone service, only `DataRepository`'s internals need to change (in-process background loop -> HTTP client against that service); no component code would need to move.

On top of `DataRepository`, the file-based `@cache_json` decorator (`src/utils/file_cache.py`) is still what actually rate-limits each external API call - see [Component Development & Rate Limiting](#component-development--rate-limiting) below.

### Presence detection

Presence (`components/header`) is a bit different: it scans the LAN (ping + targeted ARP) rather than calling an external API, but it follows the same "one shared background scan, not one per browser tab" principle via `DataRepository` - the scan runs on its own interval in the background, and each connected client's clock/presence poll just re-renders the latest already-scanned state instead of triggering new network I/O.

Detection flow, per configured person:
1. (Optional wake) ICMP ping attempts per configured IP
2. Targeted ARP request for that IP
3. MAC match validation (with a warning on mismatch)
4. Grace-window debouncing (a device is considered "home" until the grace period expires after its last positive sighting)

### Tiles, panels and taps

The page is a CSS grid of **tiles** (`BaseComponent.tile_layout`) plus every component's **detail panel** (`BaseComponent.panel_layout`), all rendered up front by `app/core_layout.py` (a layout *function*, so each page load starts from the latest cached data). Panels sit hidden in one overlay and are shown/hidden by `src/assets/dashboard.js` - plain DOM code, not Dash callbacks:

- A tap on a tile (`[data-open]`) is tracked with pointer down/up on the tile frame, which is never re-rendered, so one tap always opens its panel immediately - no server round-trip, nothing to render at tap time, and a background refresh replacing the tile's contents mid-tap can't swallow it. The synthetic click that follows the tap is swallowed so it can't land on a button inside the freshly opened panel.
- Panels return home after `PANEL_TIMEOUT_SECONDS` (`src/utils/constants.py`) of inactivity, shown as a draining ring in the panel header; any touch resets it. The Home button / Escape close immediately.
- The clock, filter chips (`[data-filter-group]` / `[data-filter-key]`) and headline rotation (`[data-rotate]`) are also handled there, so the Dash renderer isn't kept busy once a second on a slow tablet.

### Design system

Styling lives almost entirely in `src/assets/main.css` as classes; Python renders semantic markup via small builders in `src/utils/ui.py` (`badge`, `section`, `stat`, `empty_state`, `filter_chips`, ...). The few colours Python needs (TfL line colours, weather icon tints, Plotly figures, calendar colours) come from `src/utils/styles.py` - keep its tokens in sync with the `:root` custom properties at the top of `main.css`.

- **Dark, card-based layout** tuned for a wall-mounted tablet: each tile has an accent-tinted icon, an uppercase title, an optional status badge (e.g. "Rain likely 16:00", "Weaver: Good service", "1 overdue") and a chevron that signals it can be tapped.
- **Responsive to the screen, not hard-coded to one:** the root font size is `2vmin` (16px on an 800x1280 tablet), everything else is in rem, and `grid-template-areas` switch between a portrait and a landscape arrangement. Nothing scrolls on the dashboard; long lists fade out at the tile edge.
- **Colour has meaning:** teal = now/today/good, red only for genuinely urgent states (imminent departure, overdue, severe disruption), gold for warmth/sun, blue for rain.
- **Cheap to render:** transform/opacity transitions only, no `backdrop-filter`, sparklines are tiny inline SVGs (`src/utils/sparkline.py`), and the Inter typeface is loaded from Google Fonts in `app/main.py`.

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
- **Weather** - Current conditions and multi-day forecast (WeatherAPI.com), plus an hourly temperature/rain-chance chart in the detail panel
- **Google Calendar** - Today and tomorrow on the dashboard, a day-by-day agenda for the next five weeks in the detail panel; each calendar keeps a consistent colour (by `GOOGLE_CALENDAR_ID_n` order) and birthdays get a cake icon
- **TFL Transport** - Real-time London public transport arrivals, line status, and disruptions
- **Tasks** - Household people, one-off chores, and recurring chores with overdue highlighting
- **Sports Fixtures** - Upcoming matches across configured teams/sports, scraped from Where's The Match
- **Markets** - S&P 500, FTSE 100 and ACWI with weekly sparklines; 3-month charts and 52-week range in the detail panel (Yahoo Finance, no key)
- **News** - Rotating headlines from an RSS feed (default BBC News), full list in the detail panel (not on the dashboard by default - add `News()` to `COMPONENTS` and give it a grid area in `main.css`)

Tap any tile to open its detail panel; it returns home after a period of inactivity (the ring in the top-right counts down, and any touch resets it), or tap **Home**. The refresh icon in a panel's header force-clears that component's cache and refetches immediately.

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
2. **No external invalidation** - stale data persists until the cache naturally expires; use the refresh button in a component's detail panel, or a shorter lifetime, if that matters for a given component.
3. **No automatic cleanup** of old cache files - `magic-mirror-cache/`/`~/.cache/magic_mirror/` will grow slowly over time.
4. **Argument hashing** is based on the string representation of arguments (MD5) - fine for simple hashable arguments, not guaranteed stable for complex objects.
