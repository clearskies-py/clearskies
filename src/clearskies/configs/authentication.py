from __future__ import annotations

from typing import TYPE_CHECKING, Self, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.authentication import Authentication as AuthenticationType
    from clearskies.di import Di


class Authentication(config.Config):
    """Configuration descriptor that validates and stores an Authentication instance."""

    _injectables_loaded: str = ""
    di: Di

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

        authentication = instance._get_config(self)
        if hasattr(self, "di") and self.di.has_class_override(authentication.__class__):
            return self.di.get_override_by_class(authentication)
        return authentication

    @classmethod
    def injectable_properties(cls, di: Di):
        cache_name = str(cls) + str(di._serial)
        if cache_name == cls._injectables_loaded:
            return

        cls.di = di
