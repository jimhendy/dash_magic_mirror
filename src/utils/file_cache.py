import datetime
import json
import time
from collections.abc import Callable
from functools import wraps
from hashlib import md5
from pathlib import Path
from typing import Any, TypeVar, cast

from loguru import logger

from components.base import BaseComponent
from utils.dates import utc_now

CACHE_PATH = Path.home() / ".cache" / "magic_mirror"
CACHE_PATH.mkdir(parents=True, exist_ok=True)

DT_FORMAT = "%Y%m%d-%H%M%S"
_CACHED_FUNCTION_NAMES: set[str] = set()

# In-memory cache index with TTL for performance
_CACHE_INDEX: dict[str, tuple[Path, float]] = {}  # key -> (path, indexed_at_timestamp)
_INDEX_TTL_SECONDS = 5.0  # Re-scan filesystem after 5 seconds


def _get_cached_files_indexed(
    cache_key: str, arg_hash: str,
) -> dict[Path, datetime.datetime]:
    """Get cached files using in-memory index when possible."""
    cache_file_pattern = f"{cache_key}_{arg_hash}_*"
    index_key = f"{cache_key}_{arg_hash}"
    now_ts = time.time()

    # Check in-memory index first
    if index_key in _CACHE_INDEX:
        cached_path, indexed_at = _CACHE_INDEX[index_key]
        # If index is fresh and file still exists, use it
        if (now_ts - indexed_at) < _INDEX_TTL_SECONDS and cached_path.exists():
            try:
                write_time_str = cached_path.stem.split("_")[-1]
                write_time = datetime.datetime.strptime(
                    write_time_str, DT_FORMAT,
                ).replace(
                    tzinfo=datetime.UTC,
                )
                return {cached_path: write_time}
            except (ValueError, IndexError):
                # Index corrupted, fall through to filesystem scan
                pass

    # Fall back to filesystem glob (and update index)
    cache_files = {}
    for f in CACHE_PATH.glob(cache_file_pattern.replace("*", "*.json")):
        try:
            write_time = datetime.datetime.strptime(
                f.stem.split("_")[-1],
                DT_FORMAT,
            ).replace(tzinfo=datetime.UTC)
            cache_files[f] = write_time
        except (ValueError, IndexError):
            continue

    # Update index with latest file if found
    if cache_files:
        latest_file = max(cache_files, key=cache_files.get)
        _CACHE_INDEX[index_key] = (latest_file, now_ts)

    return cache_files


def reproduce_hash(*args, **kwargs) -> str:
    """Generate a reproducible hash for the given arguments."""
    # Convert args and kwargs to a consistent string representation
    args = [a for a in args if not isinstance(a, BaseComponent)]
    combined_str = f"{args!r}{kwargs!r}"
    return md5(combined_str.encode("utf-8")).hexdigest()[:8]


def clear_component_cache(component_name: str) -> int:
    """Clear all cache files for a specific component.

    Args:
        component_name: The name of the component to clear cache for

    Returns:
        Number of cache files removed

    """
    if not CACHE_PATH.exists():
        return 0

    removed_count = 0
    # Find all cache files that contain the component name
    for cache_file in CACHE_PATH.glob("*.json"):
        # Cache files are named like: module.function_hash_timestamp.json
        # Look for files that contain the component name in the module path
        if component_name.lower() in cache_file.name.lower():
            try:
                cache_file.unlink()
                removed_count += 1
            except OSError:
                # File might have been deleted by another process
                pass

    return removed_count


F = TypeVar("F", bound=Callable[..., Any])


def cache_json(valid_lifetime: datetime.timedelta) -> Callable[[F], F]:
    """Decorator to cache the result of a function to a file for a specified duration.

    The wrapped function preserves its parameter and return types for type checkers.
    """

    def decorator(func: F) -> F:
        mod = getattr(func, "__module__", func.__class__.__module__)
        name = getattr(func, "__name__", func.__class__.__name__)
        cache_key = f"{mod}.{name}"

        if cache_key in _CACHED_FUNCTION_NAMES:
            raise ValueError(f"Function {cache_key} is already cached.")
        _CACHED_FUNCTION_NAMES.add(cache_key)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper function that checks for a cached result and returns it if valid,
            otherwise calls the original function and caches its result.
            """
            arg_hash = reproduce_hash(*args, **kwargs)
            cache_file_name = f"{cache_key}_{arg_hash}_{{write_time}}.json"
            now = utc_now()

            # Use optimized indexed lookup
            cache_files = _get_cached_files_indexed(cache_key, arg_hash)

            valid_files = {
                f: t for f, t in cache_files.items() if t + valid_lifetime > now
            }
            if valid_files:
                latest_file = max(valid_files, key=valid_files.get)
                try:
                    with open(latest_file) as f:
                        return json.load(f)
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Corrupt cache file {latest_file.name} for {cache_key}: {e}. Refetching...",
                    )
                    try:
                        latest_file.unlink(missing_ok=True)
                    except OSError:
                        pass
                except OSError as e:
                    logger.warning(
                        f"Failed reading cache file {latest_file.name} for {cache_key}: {e}. Refetching...",
                    )
            else:
                logger.debug(f"No valid cache found for {cache_key}")
                for f in cache_files:
                    try:
                        f.unlink(missing_ok=True)
                    except OSError:
                        pass
            # Call the function and cache its result
            result = func(*args, **kwargs)
            cache_file = CACHE_PATH / cache_file_name.format(
                write_time=now.strftime(DT_FORMAT),
            )
            try:
                with open(cache_file, "w") as f:
                    json.dump(result, f, indent=4)
                # Update index with newly written file
                index_key = f"{cache_key}_{arg_hash}"
                _CACHE_INDEX[index_key] = (cache_file, time.time())
            except OSError as e:
                logger.error(
                    f"Failed writing cache file {cache_file.name} for {cache_key}: {e}",
                )
            return result

        return cast("F", wrapper)

    return decorator
