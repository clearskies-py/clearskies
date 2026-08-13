"""Configuration descriptor for ResponseAdapter or callable response extractors."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Self, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.backends.adapters import ResponseAdapter as ResponseAdapterType


class ResponseAdapter(config.Config):
    """
    Configuration descriptor that accepts a ``ResponseAdapter`` instance or a callable.

    A ``ResponseAdapter`` subclass provides separate ``extract_records`` and
    ``extract_record`` hooks for full control over response-envelope unwrapping.

    A plain callable ``(response_data: Any) -> list | dict | None`` may be
    supplied for simple cases where the same extraction logic covers both list
    and single-record responses.

    Example — full adapter::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            response_adapter=MyHalResponseAdapter(),
        )

    Example — inline callable::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            response_adapter=lambda data: data.get("items"),
        )
    """

    def __set__(self, instance: Any, value: ResponseAdapterType | Callable[..., Any] | None) -> None:
        if value is not None and not hasattr(value, "extract_records") and not callable(value):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter "
                "that requires a ResponseAdapter instance or a callable."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> ResponseAdapterType | Callable[..., Any] | None: ...
    def __get__(self, instance: Any, parent: type) -> Self | ResponseAdapterType | Callable[..., Any] | None:
        if not instance:
            return self
        return instance._get_config(self)
