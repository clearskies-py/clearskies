from __future__ import annotations

from typing import TYPE_CHECKING, Self, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.cursors import Cursor as CursorBase


class Cursor(config.Config):
    """Configuration descriptor that validates and stores a database cursor instance."""

    def __set__(self, instance, value: CursorBase):
        if value is not None and not hasattr(value, "build_connection_kwargs"):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a cursor."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> CursorBase: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
