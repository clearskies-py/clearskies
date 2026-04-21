from __future__ import annotations

from typing import TYPE_CHECKING, Self, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies import typing


class Joins(config.Config):
    """Configuration descriptor that validates and stores query join expressions."""

    def __set__(self, instance, value: typing.join | list[typing.join]):
        if not isinstance(value, list):
            value = [value]

        for index, item in enumerate(value):
            if callable(item) or isinstance(item, str):
                continue

            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{item.__class__.__name__}' for item #{index + 1} when a string or callable is required"
            )

        instance._set_config(self, [*value])

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> list[typing.join]: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
