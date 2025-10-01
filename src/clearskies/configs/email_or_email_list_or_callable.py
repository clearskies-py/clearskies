from __future__ import annotations

from typing import Callable

from clearskies.configs import config


class EmailOrEmailListOrCallable(config.Config):
    """
    This is for a configuration that should be an email or a list of emails or a callable that returns a list of emails.

    This is a combination of Email and EmailListOrCallable.
    """

    def __init__(
        self, required=False, default=None, regexp: str = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    ):
        self.required = required
        self.default = default
        self.regexp = regexp

    def __set__(self, instance, value: str | list[str] | Callable[..., list[str]]):
        if value is None:
            return
        if self.regexp:
            import re
        if isinstance(value, str):
            if self.regexp and not re.match(self.regexp, value):
                error_prefix = self._error_prefix(instance)
                raise ValueError(
                    f"{error_prefix} attempt to set a value of '{value}' but this does not match the required regexp: '{self.regexp}'."
                )
            value = [value]
        elif not isinstance(value, list) and not callable(value):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that should be a list or a callable"
            )
        if isinstance(value, list):
            if self.regexp:
                import re

            for index, item in enumerate(value):
                if not isinstance(item, str):
                    error_prefix = self._error_prefix(instance)
                    raise TypeError(
                        f"{error_prefix} attempt to set a value of type '{item.__class__.__name__}' for item #{index + 1}.  A string was expected."
                    )
                if not re.match(self.regexp, item):
                    error_prefix = self._error_prefix(instance)
                    raise ValueError(
                        f"{error_prefix} attempt to set a value of '{item}' for item #{index + 1} but this does not match the required regexp: '{self.regexp}'."
                    )
        instance._set_config(self, value)

    def __get__(self, instance, parent) -> list[str] | Callable[..., list[str]]:
        if not instance:
            return self  # type: ignore
        return instance._get_config(self)
