from __future__ import annotations

from typing import TYPE_CHECKING

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.authentication import Authorization as AuthorizationType
    from clearskies.di import Di


class Authorization(config.Config):
    """Configuration descriptor that validates and stores an Authorization instance."""

    _injectables_loaded: str = ""
    di: Di

    def __set__(self, instance, value: AuthorizationType):
        if not hasattr(value, "gate"):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to parameter that requires an instance of clearskies.authentication.Authorization."
            )
        instance._set_config(self, value)

    def __get__(self, instance, parent) -> AuthorizationType:
        if not instance:
            return self  # type: ignore

        authorization = instance._get_config(self)
        if hasattr(self, "di") and self.di.has_class_override(authorization.__class__):
            return self.di.get_override_by_class(authorization)
        return authorization

    @classmethod
    def injectable_properties(cls, di: Di):
        cache_name = str(cls) + str(di._serial)
        if cache_name == cls._injectables_loaded:
            return

        cls.di = di
