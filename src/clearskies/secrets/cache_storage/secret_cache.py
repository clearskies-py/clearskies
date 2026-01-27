"""
Abstract base class for secret cache storage.

This module provides the base class for implementing secret cache storage
to external stores (e.g., AWS Parameter Store, AWS Secrets Manager, Redis, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from clearskies import configurable, loggable
from clearskies.di.injectable_properties import InjectableProperties


class SecretCache(ABC, configurable.Configurable, loggable.Loggable, InjectableProperties):
    """
    Abstract base class for secret cache storage.

    This class provides the interface for implementing secret cache storage backends.
    Concrete implementations can cache secrets in various stores such as in-memory,
    Redis, AWS Parameter Store, AWS Secrets Manager, etc.

    To create a custom cache storage, extend this class and implement the abstract methods:

    ```python
    from clearskies.secrets.cache_storage import SecretCache


    class RedisCache(SecretCache):
        def __init__(self, redis_client):
            super().__init__()
            self._redis = redis_client

        def get(self, path: str) -> str | None:
            return self._redis.get(path)

        def set(self, path: str, value: str, ttl: int | None = None) -> None:
            if ttl:
                self._redis.setex(path, ttl, value)
            else:
                self._redis.set(path, value)

        def delete(self, path: str) -> None:
            self._redis.delete(path)

        def clear(self) -> None:
            self._redis.flushdb()
    ```

    Then use it with a secrets provider:

    ```python
    from clearskies.secrets import Akeyless

    cache = RedisCache(redis_client)
    akeyless = Akeyless(
        access_id="p-xxx",
        cache_storage=cache,
    )

    # First call fetches from Akeyless and caches
    secret = akeyless.get("/path/to/secret")

    # Subsequent calls return cached value
    secret = akeyless.get("/path/to/secret")

    # Force refresh bypasses cache
    secret = akeyless.get("/path/to/secret", refresh=True)
    ```
    """

    @abstractmethod
    def get(self, path: str) -> str | None:
        """
        Retrieve a cached secret value.

        Returns the cached secret value for the given path, or None if not found or expired.
        """
        pass

    @abstractmethod
    def set(self, path: str, value: str, ttl: int | None = None) -> None:
        """
        Store a secret value in the cache.

        Stores the secret value under the given path. If ttl is provided, the entry will
        expire after that many seconds. If ttl is None, the cache implementation may use
        a default TTL or store indefinitely.
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """
        Remove a secret from the cache.

        Removes the secret at the given path from the cache. Does nothing if the path
        doesn't exist.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all secrets from the cache.

        Use with caution in production environments.
        """
        pass
