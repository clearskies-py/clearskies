from __future__ import annotations

from typing import TYPE_CHECKING, Self, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.secrets import Secrets as SecretsBase


class Secrets(config.Config):
    """
    Configuration descriptor for a secret manager.

    This config validates that the provided value is a clearskies.Secrets instance.

    Usage:
        ```python
        from clearskies import configs


        class UsesSecrets(configs.Configurable):
            secrets_manager = configs.SecretsManager(required=True)

            def __init__(self, secrets_manager: clearskies.Secrets):
                self.secrets_manager = secrets_manager
                self.finalize_and_validate_configuration()
        ```
    """

    def __set__(self, instance, value: SecretsBase | None):
        if value is not None:
            # Import here to avoid circular imports
            from clearskies.secrets import Secrets as SecretsBase

            if not isinstance(value, SecretsBase):
                error_prefix = self._error_prefix(instance)
                raise TypeError(
                    f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' "
                    "to a parameter that requires an instance of clearskies.Secrets."
                )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> SecretsBase | None: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
