from __future__ import annotations

import datetime
from typing import Self, overload

from clearskies.configs import config


class Timezone(config.Config):
    def __set__(self, instance, value: datetime.timezone | None):
        if value and not isinstance(value, datetime.timezone):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a timezone (datetime.timezone)."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> datetime.timezone: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
