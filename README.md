# Magic Mirror Dashboard

A modern, customizable magic mirror dashboard built with Dash and Python. Features a clean single-line layout with real-time data from multiple sources including London Transport arrivals, weather, calendar events, sports fixtures, and news feeds.

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
   uv run src/app/main.py
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
- Health checks
- Read-only mounting of configuration files

## Configuration

The application uses environment variables and `src/app/config.py` for configuration. 

### Component Configuration

All components can be enabled/disabled and configured with header icons and titles in `src/app/config.py`:

```python
# Component definitions with header icons and titles
COMPONENTS = {
    "clock": {
        "enabled": True,
        "component": ClockComponent(),
        "header_icon": "tabler:clock",
        "header_title": "Time"
    },
    "weather": {
        "enabled": True, 
        "component": WeatherComponent(),
        "header_icon": "tabler:cloud",
        "header_title": "Weather"
    },
    "google_calendar": {
        "enabled": True,
        "component": GoogleCalendarComponent(),
        "header_icon": "tabler:calendar",
        "header_title": "Calendar"
    },
    "tfl_arrivals": {
        "enabled": True,
        "component": TFLArrivalsComponent(), 
        "header_icon": "tabler:train",
        "header_title": "Transport"
    },
    "sports": {
        "enabled": True,
        "component": SportsComponent(),
        "header_icon": "tabler:ball-football",
        "header_title": "Sports"
    },
    "news": {
        "enabled": True,
        "component": NewsComponent(),
        "header_icon": "tabler:news", 
        "header_title": "News"
    },
    "compliments_jokes": {
        "enabled": True,
        "component": ComplimentsJokesComponent(),
        "header_icon": "tabler:mood-smile",
        "header_title": "Daily Inspiration"
    }
}
```

### Environment Variables

Copy `.env.example` to `.env` and customize:

- **TFL Stops**: Configure transport stop IDs and display names
- **Weather**: Set your postcode and WeatherAPI key  
- **Google Calendar**: Configure calendar integration (optional)
- **Layout**: Adjust component positioning and sizing

## API Setup

### TFL Stop IDs

To find your local London transport stops:
1. Visit https://api.tfl.gov.uk/StopPoint/Search/{your-area}
2. Find your stop and note the `id` field
3. Update your `.env` file with the stop ID and display name

### Weather API

1. Get a free API key from [WeatherAPI.com](https://www.weatherapi.com/signup.aspx)
2. Add your API key to `.env` as `WEATHER_API_KEY`
3. Set your postcode in `WEATHER_POSTCODE` (e.g., "SW1A 1AA")

### Google Calendar (Optional)

1. Set up Google Calendar API credentials
2. Place `google_calendar_credentials.json` in the `credentials/` folder
3. The component will automatically integrate calendar events

### Sports & News

- Sports fixtures are fetched from BBC Sport
- News feeds use RSS sources (configurable in component)
- Both work out-of-the-box without additional API keys

## Features

### Core Components

- **🕐 Live Clock** - Real-time display with date formatting
- **🌤️ Weather Forecast** - Current conditions and 3-day outlook with WeatherAPI integration
- **📅 Google Calendar** - Upcoming events with smart date formatting and birthday icons
- **🚇 TFL Transport** - Real-time London public transport arrivals with color-coded timing
- **⚽ Sports Fixtures** - Upcoming matches across multiple sports with team information
- **📰 News Feed** - Rotating headlines from RSS sources with 8-second intervals
- **💭 Compliments & Jokes** - Rotating positive messages and humor (1000+ items)

### Design Features

- **Unified Visual Language** - Consistent single-line card layouts across all components
- **Modern Glass Effect** - Gradient backgrounds with backdrop filters for elegant depth
- **Responsive Typography** - Inter/Roboto font stacks with consistent sizing hierarchy
- **Color-Coded Information** - Red for urgent items, golden accents for active events
- **Visual Separators** - Icon-based dividers between component sections
- **Flexible Positioning** - Fractional coordinate system for precise layout control

### Technical Features

- **Smart Caching System** - File-based API rate limiting with configurable lifetimes
- **Component Architecture** - Modular design with BaseComponent inheritance
- **Auto-Refresh** - Real-time updates without manual intervention
- **Health Monitoring** - Built-in health checks for Docker deployment
- **Error Resilience** - Graceful handling of API failures and network issues

## Architecture & Design

### Component System

The Magic Mirror uses a modular component architecture with consistent design patterns:

#### BaseComponent Abstract Class

All components inherit from `BaseComponent` in `src/components/base.py`:

```python
class BaseComponent(ABC):
    def __init__(self, header_icon: str = None, header_title: str = None):
        self.header_icon = header_icon
        self.header_title = header_title
    
    @abstractmethod
    def layout(self) -> html.Div:
        """Return the component's layout."""
        pass
    
    @abstractmethod  
    def register_callbacks(self, app):
        """Register component-specific callbacks."""
        pass
```

#### Consistent Design Language

All components follow the same visual patterns:

- **Single-line layouts** - Information organized horizontally for clean presentation
- **Card-based design** - Each item in a consistent card with 8px border radius
- **Consistent spacing** - 8px gaps between items, 12px 14px padding within cards
- **Unified typography** - 1.2rem headers, 1.1rem main content, 0.9rem secondary info
- **Color consistency** - COLORS palette from `utils.styles` used throughout
- **Glass effect** - Gradient backgrounds with subtle transparency

#### Visual Separators

Components are visually separated using icon-based dividers:

```python
def create_separator(icon: str, title: str) -> html.Div:
    return html.Div([
        DashIconify(icon=icon, width=20, color=COLORS['text']),
        html.Span(title, style={"marginLeft": "8px", "fontSize": "1rem"})
    ], style={
        "display": "flex", "alignItems": "center",
        "marginBottom": "12px", "color": COLORS['text']
    })
```

### Layout System

- **Percentage-based heights** - Each component gets allocated screen real estate
- **Flexbox containers** - Responsive layouts that adapt to content
- **Single-column flow** - Components stacked vertically with separators
- **Gradient backgrounds** - Modern glass effect throughout the interface

### Component Capabilities

#### Clock Component (`clock.py`)
- Real-time display with automatic updates
- Formatted date and time with weekday
- Compact single-line presentation

#### Weather Component (`weather.py`)
- Current conditions with temperature and "feels like"
- 3-day forecast with weather icons
- WeatherAPI.com integration with error handling

#### Google Calendar Component (`google_calendar.py`)
- Upcoming events with smart date formatting
- Birthday detection with cake icons
- Single-line layout with event title left, date/time right
- Golden accents for today's events

#### TFL Arrivals Component (`tfl_arrivals.py`)
- Real-time London transport arrivals
- Multiple station support with unified display
- Color-coded timing (red for <2min, normal for longer)
- Station name + line displayed with arrival times

#### Sports Component (`sports.py`)
- Multi-sport fixture support (Football, Rugby, Cricket, Tennis, F1)
- Today's matches highlighted with enhanced styling
- Team information with competition context
- BBC Sport integration for reliable data

#### News Component (`news.py`)
- Rotating headlines with 8-second intervals
- RSS feed integration (BBC News by default)
- Source attribution for each headline
- Smooth transitions between stories

#### Compliments & Jokes Component (`compliments_jokes.py`)
- 1000+ positive messages and jokes
- Time-based rotation for fresh content
- Mood-lifting content to start the day
- Local content (no API dependencies)

## Component Development & Rate Limiting

### Cache JSON Decorator

The `@cache_json` decorator in `src/utils/file_cache.py` provides file-based caching for component data fetching functions. This decorator is **essential** for implementing rate limiting and preventing excessive API calls.

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
- **Weather**: `30 minutes` - Weather conditions update periodically
- **Google Calendar**: `1 hour` - Calendar events don't change often during the day
- **Sports**: `6 hours` - Match schedules are relatively static
- **News**: `15 minutes` - News headlines update regularly
- **Compliments/Jokes**: No caching - Static local content

### **CRITICAL: Component Rate Limiting Requirements**

⚠️ **Component developers MUST implement proper rate limiting** ⚠️

When multiple clients (browser instances, development servers, etc.) access your Magic Mirror application simultaneously, each client will trigger its own data fetching cycle. Without proper rate limiting, this can lead to:

1. **API quota exhaustion** - Hitting rate limits on external APIs
2. **Increased latency** - Too many concurrent requests slowing down responses  
3. **Potential service blocking** - APIs may temporarily ban your IP address
4. **Resource waste** - Unnecessary network and computational overhead

**The `@cache_json` decorator makes rate limiting trivial to implement.** Simply:

1. Decorate your `fetch()` method with `@cache_json(valid_lifetime=...)`
2. Choose an appropriate cache lifetime for your data source
3. The decorator handles all caching logic automatically

### Design Flaws & Considerations

While the `cache_json` decorator provides effective rate limiting, there are some design limitations to be aware of:

#### 1. **File System Race Conditions**
- **Issue**: Multiple processes writing cache files simultaneously could cause corruption
- **Impact**: Rare, but could result in cache misses or invalid JSON
- **Mitigation**: Consider file locking for high-concurrency scenarios

#### 2. **Cache Invalidation Complexity**
- **Issue**: No mechanism to invalidate cache based on external events
- **Impact**: Stale data may persist until cache expires naturally
- **Mitigation**: Use shorter cache lifetimes for critical data or implement manual cache clearing

#### 3. **Memory vs Disk Trade-off**
- **Issue**: File I/O overhead for each cache access
- **Impact**: Slightly slower than in-memory caching
- **Benefit**: Persistent across application restarts and shared between processes

#### 4. **Cache Size Growth**
- **Issue**: No automatic cleanup of old cache directories
- **Impact**: Disk usage can grow over time
- **Mitigation**: Consider implementing periodic cleanup of the cache directory

#### 5. **Argument Serialization Limitations**
- **Issue**: MD5 hash is based on string representation of arguments
- **Impact**: Complex objects might not hash consistently
- **Mitigation**: Use simple, hashable arguments or implement custom serialization

#### 6. **No Cache Warming**
- **Issue**: First request after cache expiration will be slow
- **Impact**: Users may experience delays during cache refresh
- **Mitigation**: Consider background cache refresh for critical components

Despite these limitations, the `cache_json` decorator provides a robust, simple solution for most Magic Mirror component caching needs.
