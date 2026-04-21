from __future__ import annotations

from typing import Callable, Self, overload

from clearskies.configs import config


class BooleanOrCallable(config.Config):
    """Configuration descriptor that accepts a boolean or a callable returning a boolean."""

    def __set__(self, instance, value: bool | Callable[..., bool]):
        if not isinstance(value, bool) and not callable(value):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a boolean or a callable."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> bool | Callable[..., bool]: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
