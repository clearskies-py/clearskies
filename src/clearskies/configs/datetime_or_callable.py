from __future__ import annotations

import datetime
from typing import Callable, Self, overload

from clearskies.configs import config


class DatetimeOrCallable(config.Config):
    def __set__(self, instance, value: datetime.datetime | Callable[..., datetime.datetime]):
        if not isinstance(value, datetime.datetime) and not callable(value):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a datetime object or a callable."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> datetime.datetime | Callable[..., datetime.datetime]: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
