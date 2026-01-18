from __future__ import annotations

from typing import TYPE_CHECKING

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.cursors import Cursor as CursorBase


class Cursor(config.Config):
    def __set__(self, instance, value: CursorBase):
        if not hasattr(value, "build_connection_kwargs"):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a cursor."
            )
        instance._set_config(self, value)

    def __get__(self, instance, parent) -> CursorBase:
        if not instance:
            return self  # type: ignore
        return instance._get_config(self)
