import datetime
import json
from collections.abc import Callable
from functools import wraps
from hashlib import md5
from pathlib import Path

from components.base import BaseComponent

CACHE_PATH = Path.home() / ".cache" / "magic_mirror"
CACHE_PATH.mkdir(parents=True, exist_ok=True)

DT_FORMAT = "%Y%m%d-%H%M%S"
_CACHED_FUNCTION_NAMES = set()

def reproduce_hash(*args, **kwargs) -> str:
    """Generate a reproducible hash for the given arguments."""
    # Convert args and kwargs to a consistent string representation
    args = [a for a in args if not isinstance(a, BaseComponent)]
    combined_str = f"{args!r}{kwargs!r}"
    return md5(combined_str.encode("utf-8")).hexdigest()[:8]


def cache_json(valid_lifetime: datetime.timedelta) -> Callable:
    """Decorator to cache the result of a function to a file for a specified duration."""

    def decorator(func: Callable) -> Callable:

        cache_key = f"{func.__module__}.{func.__name__}"

        if cache_key in _CACHED_FUNCTION_NAMES:
            raise ValueError(f"Function {cache_key} is already cached.")
        _CACHED_FUNCTION_NAMES.add(cache_key)

        @wraps(func)
        def wrapper(*args, **kwargs) -> dict:
            """Wrapper function that checks for a cached result and returns it if valid,
            otherwise calls the original function and caches its result.
            """
            # Ensure the cache directory exists
            arg_hash = reproduce_hash(*args, **kwargs)
            cache_file_name = f"{cache_key}_{arg_hash}_{{write_time}}.json"
            now = datetime.datetime.now(tz=datetime.UTC)
            # Find the most recent valid cache file
            cache_files = {
                f: datetime.datetime.strptime(
                    f.stem.split("_")[-1],
                    DT_FORMAT,
                ).astimezone(tz=datetime.UTC)
                for f in CACHE_PATH.glob(cache_file_name.format(write_time="*"))
            }
            valid_files = {
                f: t for f, t in cache_files.items() if now - t < valid_lifetime
            }
            if valid_files:
                # Use the most recent valid cache file
                latest_file = max(valid_files, key=valid_files.get)
                with open(latest_file) as f:
                    return json.load(f)
            else:
                # Remove old cache files
                for f in cache_files:
                    f.unlink(missing_ok=True)
                # Call the function and cache its result
                result = func(*args, **kwargs)
                cache_file = CACHE_PATH / cache_file_name.format(
                    write_time=now.strftime(DT_FORMAT),
                )
                with open(cache_file, "w") as f:
                    json.dump(result, f, indent=4)
                return result

        return wrapper

    return decorator
