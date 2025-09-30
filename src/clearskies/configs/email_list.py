from __future__ import annotations

from clearskies.configs import config


class EmailList(config.Config):
    """
    This is for a configuration that should be a list of strings.

    This is different than StringList, which also accepts a list of strings, but
    validates that all of those values match the required format.
    """

    def __init__(
        self, required=False, default=None, regexp: str = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    ):
        self.required = required
        self.default = default
        self.regexp = regexp

    def __set__(self, instance, value: list[str], regexp: str = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"):
        if value is None:
            return

        if not isinstance(value, list):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a list of strings parameter."
            )
        if self.regexp:
            import re

        for index, item in enumerate(value):
            if not isinstance(item, str):
                error_prefix = self._error_prefix(instance)
                raise TypeError(
                    f"{error_prefix} attempt to set a value of type '{item.__class__.__name__}' for item #{index + 1}. A string was expected."
                )
            if not re.match(self.regexp, item):
                error_prefix = self._error_prefix(instance)
                raise ValueError(
                    f"{error_prefix} attempt to set a value of '{item}' for item #{index + 1} but this does not match the required regexp: '{self.regexp}'."
                )
        instance._set_config(self, value)

    def __get__(self, instance, parent) -> list[str]:
        if not instance:
            return self  # type: ignore
        return instance._get_config(self)
