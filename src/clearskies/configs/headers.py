from __future__ import annotations

from typing import TYPE_CHECKING, Self, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.input_outputs import headers


class Headers(config.Config):
    """This is for a configuration that should be an instance of type clearskies.input_outputs.Headers."""

    def __set__(self, instance, value: headers.Headers):
        if value is None:
            return

        if not hasattr(value, "_duck_cheat") or value._duck_cheat != "headers":
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a property that expets an instance of clearskies.input_outputs.Headers"
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> headers.Headers: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
