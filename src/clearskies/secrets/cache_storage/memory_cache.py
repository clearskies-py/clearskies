"""
In-memory cache storage for secrets.

This module provides a simple in-memory cache implementation with optional TTL support.
Useful for development, testing, or scenarios where secrets don't need to persist
across process restarts.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from clearskies.di import inject
from clearskies.secrets.cache_storage.secret_cache import SecretCache


@dataclass
class CacheEntry:
    """A cached value with optional expiration time."""

    value: str
    expires_at: datetime.datetime | None = None

    def is_expired(self, now: datetime.datetime) -> bool:
        """Check if this cache entry has expired."""
        if self.expires_at is None:
            return False
        return now > self.expires_at


class MemoryCache(SecretCache):
    """
    In-memory cache storage for secrets.

    This implementation stores secrets in a Python dictionary with optional TTL support.
    Expired entries are lazily cleaned up on access. The current time is injected via
    the dependency injection system, making it easy to mock time in tests.

    ### Example Usage

    ```python
    from clearskies.secrets.cache_storage import MemoryCache
    from clearskies.secrets.akeyless import Akeyless

    # Create cache with default 5-minute TTL
    cache = MemoryCache(default_ttl=300)

    akeyless = Akeyless(
        access_id="p-xxx",
        cache_storage=cache,
    )

    # First call fetches from Akeyless and caches for 5 minutes
    secret = akeyless.get("/path/to/secret")

    # Subsequent calls within 5 minutes return cached value
    secret = akeyless.get("/path/to/secret")

    # Force refresh bypasses cache
    secret = akeyless.get("/path/to/secret", refresh=True)
    ```

    ### Testing with Mocked Time

    The cache uses `inject.Now()` for time, which can be controlled via the DI container:

    ```python
    from clearskies.di import Di
    from clearskies.secrets.cache_storage import MemoryCache
    import datetime

    di = Di()
    di.set_now(datetime.datetime(2024, 1, 1, 12, 0, 0))

    cache = MemoryCache(default_ttl=60)
    cache.injectable_properties(di=di)

    cache.set("/secret", "value")

    # Advance time past TTL
    di.set_now(datetime.datetime(2024, 1, 1, 12, 1, 1))

    # Entry is now expired
    assert cache.get("/secret") is None
    ```
    """

    """
    The current time, injected via the dependency injection system.

    This allows time to be mocked in tests by calling `di.set_now()`.
    """
    now: Any = inject.Now()

    def __init__(self, default_ttl: int | None = None):
        """
        Initialize the memory cache.

        The default_ttl specifies the default time-to-live in seconds for cached entries.
        If None, entries never expire unless a TTL is explicitly provided when calling set().
        """
        super().__init__()
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl

    def get(self, path: str) -> str | None:
        """
        Retrieve a cached secret value.

        Returns the cached secret value for the given path, or None if not found or expired.
        Expired entries are automatically removed from the cache.
        """
        entry = self._cache.get(path)
        if entry is None:
            return None

        if entry.is_expired(self.now):
            del self._cache[path]
            return None

        return entry.value

    def set(self, path: str, value: str, ttl: int | None = None) -> None:
        """
        Store a secret value in the cache.

        Stores the secret value under the given path. If ttl is provided, it overrides
        the default_ttl. If both are None, the entry never expires.
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = self.now + datetime.timedelta(seconds=effective_ttl) if effective_ttl is not None else None

        self._cache[path] = CacheEntry(value=value, expires_at=expires_at)

    def delete(self, path: str) -> None:
        """
        Remove a secret from the cache.

        Removes the secret at the given path from the cache. Does nothing if the path
        doesn't exist.
        """
        if path in self._cache:
            del self._cache[path]

    def clear(self) -> None:
        """Remove all secrets from the cache."""
        self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        This is called automatically during get() for individual entries, but can be
        called manually to clean up all expired entries at once. Returns the number
        of expired entries that were removed.
        """
        now = self.now
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired(now)]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    @property
    def size(self) -> int:
        """Return the number of entries in the cache (including expired)."""
        return len(self._cache)
