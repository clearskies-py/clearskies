from typing import Callable, Self, overload

from clearskies.configs import config


class StringOrCallable(config.Config):
    """Configuration descriptor that accepts a string or a callable returning a string."""

    def __set__(self, instance, value: str | Callable[..., str]):
        if not isinstance(value, str) and not callable(value):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requires a string or a callable."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> str | Callable[..., str]: ...
    def __get__(self, instance, parent):
        if not instance:
            return self
        return instance._get_config(self)
