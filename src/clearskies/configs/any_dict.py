from __future__ import annotations

from typing import Any, Self, overload

from clearskies.configs import config


class AnyDict(config.Config):
    def __set__(self, instance, value: dict[str, Any]):
        if not isinstance(value, dict):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a dictionary."
            )
        for key in value.keys():
            if not isinstance(key, str):
                error_prefix = self._error_prefix(instance)
                raise TypeError(f"{error_prefix} attempt to set a dictionary with a non-string key.")
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> dict[str, Any]: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
