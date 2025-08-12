# Magic Mirror Dashboard

A customizable magic mirror dashboard built with Dash and Python, featuring real-time London Transport (TFL) arrivals, clock, and rotating compliments/jokes.

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

The application uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

- **TFL Stops**: Configure up to 2 stops for left side and 2 stops for right side
- **Weather**: Set your postcode and WeatherAPI key
- **Component Positioning**: Fine-tune component positions and sizes
- **Layout**: Adjust positioning using fractional coordinates (0.0 to 1.0)

## API Setup

### TFL Stop IDs

To find your local transport stops:
1. Visit https://api.tfl.gov.uk/StopPoint/Search/{your-area}
2. Find your stop and note the `id` field
3. Update your `.env` file with the stop ID and a display name

### Weather API

1. Get a free API key from [WeatherAPI.com](https://www.weatherapi.com/signup.aspx)
2. Add your API key to `.env` as `WEATHER_API_KEY`
3. Set your postcode in `WEATHER_POSTCODE` (e.g., "SW1A 1AA")

## Features

- **Real-time TFL arrivals** with countdown timers
- **Weather forecast** with current conditions and 3-day outlook
- **Live clock** with date display  
- **Rotating compliments and jokes** with 1000+ items
- **Flexible positioning** system with fractional coordinates
- **Responsive design** optimized for magic mirror displays

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
- **Google Calendar**: `1 hour` - Calendar events don't change often during the day
- **Sports**: `6 hours` - Match schedules are relatively static
- **News**: `60 hours` - Less frequent updates needed

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
