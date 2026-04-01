from __future__ import annotations

from typing import Self, overload

from clearskies.configs import config


class Integer(config.Config):
    def __init__(self, required=False, default=None, min: int | None = None, max: int | None = None):
        super().__init__(required=required, default=default)
        self.min = min
        self.max = max

    def __set__(self, instance, value: int):
        if not isinstance(value, int):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to parameter that requires an integer."
            )
        if self.min is not None and value < self.min:
            error_prefix = self._error_prefix(instance)
            raise ValueError(
                f"{error_prefix} attempt to set a value of {value} which is less than the minimum allowed {self.min}."
            )
        if self.max is not None and value > self.max:
            error_prefix = self._error_prefix(instance)
            raise ValueError(
                f"{error_prefix} attempt to set a value of {value} which is greater than the maximum allowed {self.max}."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> int: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
