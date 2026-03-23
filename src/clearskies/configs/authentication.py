from __future__ import annotations

from typing import TYPE_CHECKING, Self, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.authentication import Authentication as AuthenticationType


class Authentication(config.Config):
    def __set__(self, instance, value: AuthenticationType):
        if not hasattr(value, "authenticate"):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to parameter that requires an instance of clearskies.authentication.Authentication."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> AuthenticationType: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
