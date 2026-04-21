from __future__ import annotations

from typing import Self, overload

from clearskies.configs import config


class Boolean(config.Config):
    """Configuration descriptor that validates and stores boolean values."""

    def __set__(self, instance, value: bool):
        if not isinstance(value, bool):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a boolean."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> bool: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
