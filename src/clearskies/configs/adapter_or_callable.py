"""Configuration descriptor for adapter protocols with callable fallback."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.backends.adapters import Adapter

T = TypeVar("T", bound="Adapter")


class AdapterOrCallable(config.Config, Generic[T]):
    """
    Configuration descriptor that accepts an Adapter instance or a callable.

    An Adapter instance (or subclass instance) provides protocol methods
    for handling specific concerns (URL routing, pagination extraction, etc.).

    A plain callable with compatible signature may be supplied for simple cases
    where the same logic applies uniformly.

    Example — adapter instance::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            url_adapter=MyUrlAdapter(),
        )

    Example — inline callable::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            url_adapter=lambda query: f"/api/{query.model_class.destination_name()}",
        )
    """

    def __init__(self, adapter_type: str, default: T | Callable[..., Any] | None = None):
        super().__init__(default=default)
        self.adapter_type = adapter_type

    def __set__(self, instance: Any, value: T | Callable[..., Any] | None) -> None:
        # imported here rather than at module scope to avoid a circular import
        # (configs -> adapters.adapter -> configurable -> configs)
        from clearskies.backends.adapters.adapter import Adapter

        if value is not None and not isinstance(value, Adapter) and not callable(value):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter "
                f"that requires a {self.adapter_type} instance or a callable."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> T | Callable[..., Any] | None: ...
    def __get__(self, instance: Any, parent: type) -> Self | T | Callable[..., Any] | None:
        if not instance:
            return self
        return instance._get_config(self)
