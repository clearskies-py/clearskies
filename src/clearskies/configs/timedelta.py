from __future__ import annotations

import datetime
from typing import Self, overload

from clearskies.configs import config


class Timedelta(config.Config):
    def __set__(self, instance, value: datetime.timedelta):
        if not isinstance(value, datetime.timedelta):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a datetime.timedelta object."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> datetime.timedelta: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
