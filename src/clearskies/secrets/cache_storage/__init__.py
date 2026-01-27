"""
Cache storage support for secrets.

This module provides an abstract base class for implementing secret cache storage
to external stores (e.g., AWS Parameter Store, AWS Secrets Manager, Redis, etc.),
as well as a built-in in-memory cache implementation.

The base SecretCache class can be extended to create custom cache storage
implementations. Concrete implementations typically live in separate packages.

Usage with MemoryCache:
    from clearskies.secrets.cache_storage import MemoryCache

    # Create cache with 5-minute TTL
    cache = MemoryCache(default_ttl=300)

    # Use with a secrets provider:
    # secrets = clearskies.secrets.Akeyless(
    #     access_id="p-abc123",
    #     access_type="aws_iam",
    #     cache_storage=cache,
    # )

Custom implementation:
    from clearskies.secrets.cache_storage import SecretCache

    class MySecretCache(SecretCache):
        def get(self, path: str) -> str | None:
            # Retrieve from cache
            return None

        def set(self, path: str, value: str, ttl: int | None = None) -> None:
            # Store in cache
            pass

        def delete(self, path: str) -> None:
            # Remove from cache
            pass

        def clear(self) -> None:
            # Clear all cached secrets
            pass

"""

from clearskies.secrets.cache_storage.memory_cache import MemoryCache
from clearskies.secrets.cache_storage.secret_cache import SecretCache

__all__ = ["MemoryCache", "SecretCache"]
