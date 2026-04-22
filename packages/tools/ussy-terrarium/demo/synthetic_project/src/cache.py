"""Caching utilities with Redis fallback."""

import json
import time
from typing import Any, Optional


# In-memory cache for development
_local_cache: dict = {}


def get_cache(key: str) -> Optional[Any]:
    """Get a value from cache."""
    if key in _local_cache:
        value, expires = _local_cache[key]
        if expires is None or expires > time.time():
            return value
        del _local_cache[key]
    return None


def set_cache(key: str, value: Any, ttl: Optional[int] = None):
    """Set a value in cache with optional TTL."""
    expires = time.time() + ttl if ttl else None
    _local_cache[key] = (value, expires)


def delete_cache(key: str):
    """Delete a key from cache."""
    _local_cache.pop(key, None)


def clear_cache():
    """Clear all cached values."""
    _local_cache.clear()


class CacheDecorator:
    """Decorator for caching function results."""

    def __init__(self, ttl: int = 300):
        self.ttl = ttl

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(args)}:{hash(tuple(kwargs.items()))}"
            cached = get_cache(cache_key)
            if cached is not None:
                return cached
            result = func(*args, **kwargs)
            set_cache(cache_key, result, self.ttl)
            return result

        return wrapper
