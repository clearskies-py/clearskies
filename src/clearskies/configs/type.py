from __future__ import annotations

from typing import Generic, Self, TypeVar, overload

from clearskies.configs import config

_T = TypeVar("_T")


class Type(Generic[_T], config.Config):
    """Configuration descriptor that validates and stores type values.

    Accepts either a single type or a tuple of types (mirroring Python's
    built-in ``isinstance`` support).

    Declare the descriptor with an explicit type annotation so that the LSP
    knows the precise return type when reading the attribute:

    Examples::

        # returns type | tuple[type, ...] | None
        value_type: configs.Type[type | tuple[type, ...]] = configs.Type(default=None)

        # single type only — returns type | None
        value_type: configs.Type[type] = configs.Type(default=None)

    Usage on a column::

        my_col = columns.List(value_type=str)
        my_col = columns.List(value_type=(str, int))
    """

    def __init__(self, required: bool = False, default: type | tuple[type, ...] | None = None):
        self.required = required
        self.default = default

    @property
    def has_default(self) -> bool:
        # None is a meaningful default here ("no type restriction"), so always advertise
        # that a default exists — otherwise _get_config raises KeyError when value_type
        # was never explicitly set on the column.
        return True

    def __set__(self, instance, value: type | tuple[type, ...]) -> None:
        valid = isinstance(value, type) or (
            isinstance(value, tuple) and len(value) > 0 and all(isinstance(t, type) for t in value)
        )
        if not valid:
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' "
                f"to a parameter that requires a type or a non-empty tuple of types."
            )
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> _T | None: ...
    def __get__(self, instance, parent) -> Self | _T | None:
        if not instance:
            return self
        return instance._get_config(self)
