from __future__ import annotations

from clearskies.configs import config


class IntegerOrNone(config.Config):
    """
    Config descriptor that accepts integers or None values.

    Use this when you need an optional integer parameter where None indicates
    the absence of a value, as opposed to Integer which requires a non-null integer.
    """

    def __set__(self, instance, value: int | None):
        if not isinstance(value, (int, type(None))):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to parameter that requires an integer or None."
            )
        instance._set_config(self, value)

    def __get__(self, instance, parent) -> int | None:
        if not instance:
            return self  # type: ignore
        return instance._get_config(self)
