from __future__ import annotations

from typing import TYPE_CHECKING

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.secrets.cache_storage import SecretCache as SecretCacheBase


class SecretCache(config.Config):
    """
    Configuration descriptor for secret cache storage.

    This config validates that the provided value is a SecretCache instance.

    Usage:
        ```python
        from clearskies import configs


        class MySecretsProvider(configs.Configurable):
            cache_storage = configs.SecretCache()
        ```
    """

    def __set__(self, instance, value: SecretCacheBase | None):
        if value is not None:
            # Import here to avoid circular imports
            from clearskies.secrets.cache_storage import SecretCache as SecretCacheBase

            if not isinstance(value, SecretCacheBase):
                error_prefix = self._error_prefix(instance)
                raise TypeError(
                    f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' "
                    "to a parameter that requires a SecretCache."
                )
        instance._set_config(self, value)

    def __get__(self, instance, parent) -> SecretCacheBase | None:
        if not instance:
            return self  # type: ignore
        return instance._get_config(self)
