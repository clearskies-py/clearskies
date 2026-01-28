from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

import clearskies.configurable
from clearskies import configs, loggable
from clearskies.di import inject
from clearskies.di.injectable_properties import InjectableProperties

if TYPE_CHECKING:
    from clearskies.secrets.cache_storage.secret_cache import SecretCache


class Secrets(ABC, clearskies.configurable.Configurable, InjectableProperties, loggable.Loggable):
    """
    A clearskies secrets manager.

    This is the base class for all secrets implementations, providing a unified interface for
    secret operations across different backends. It manages secret retrieval, creation, and
    updates, and supports optional cache storage.

    ### Cache Storage

    The `cache_storage` parameter accepts an instance of a subclass of
    [`SecretCache`](src/clearskies/secrets/cache_storage/secret_cache.py:1).
    This enables flexible caching strategies, such as AWS Parameter Store, AWS Secrets Manager,
    Redis, or any other cache backend. Concrete implementations can be created as needed.

    #### Example: Custom Cache Storage

    ```python
    from clearskies.secrets.cache_storage import SecretCache
    import clearskies


    class MyCache(SecretCache):
        def get(self, path: str) -> str | None:
            # Retrieve from your cache
            return None

        def set(self, path: str, value: str, ttl: int | None = None) -> None:
            # Store in your cache
            pass

        def delete(self, path: str) -> None:
            # Remove from your cache
            pass

        def clear(self) -> None:
            # Clear all cached secrets
            pass


    secrets = clearskies.secrets.Akeyless(
        access_id="p-abc123",
        access_type="aws_iam",
        cache_storage=MyCache(),
    )
    secret_value = secrets.get("/path/to/secret")
    ```

    ### Attributes

    - `cache_storage`: Optional cache storage configuration (SecretCache subclass).
    """

    """
    Optional cache storage configuration (can be a SecretCache instance).
    """
    cache_storage = configs.SecretCache(default=None)

    """Dependency injection container."""
    di = inject.Di()

    """
    Whether cache_storage has been initialized with DI
    """
    _cache_storage_active: bool = False

    @property
    def cache(self) -> SecretCache | None:
        """Get the cache storage instance."""
        if self._cache_storage_active and self.cache_storage:
            return self.cache_storage
        if self.cache_storage and hasattr(self.cache_storage, "injectable_properties"):
            self.cache_storage.injectable_properties(di=self.di)
        self._cache_storage_active = True
        return self.cache_storage

    def create(self, path: str, value: str) -> bool:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def get(self, path: str, silent_if_not_found: bool = False, refresh: bool = False) -> str:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def list_secrets(self, path: str) -> list[Any]:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def update(self, path: str, value: Any) -> None:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def upsert(self, path: str, value: Any) -> None:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def list_sub_folders(self, path: str) -> list[Any]:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def delete(self, path: str) -> bool:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )
