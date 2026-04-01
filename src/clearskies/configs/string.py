from __future__ import annotations

import re
from typing import Self, overload

from clearskies.configs import config


class String(config.Config):
    def __init__(self, required=False, default=None, regexp: str = ""):
        self.required = required
        self.default = default
        self.regexp = regexp

    def __set__(self, instance, value: str):
        if not isinstance(value, str):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requires a string."
            )
        if self.regexp:
            if not re.match(self.regexp, value):
                error_prefix = self._error_prefix(instance)
                raise ValueError(
                    f"{error_prefix} attempt to set a value of '{value}' but this does not match the required regexp: '{self.regexp}'."
                )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> str: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
