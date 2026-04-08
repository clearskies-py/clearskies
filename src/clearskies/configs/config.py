from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clearskies.di.injectable_properties import InjectableProperties

if TYPE_CHECKING:
    from clearskies.configurable import Configurable


class Config(InjectableProperties):
    """Base configuration descriptor for declaring and validating configuration options on Configurable classes."""

    def __init__(self, required: bool = False, default: Any = None) -> None:
        self.required = required
        self.default = default

    @property
    def has_default(self) -> bool:
        return self.default is not None

    def _error_prefix(self, instance: Configurable) -> str:
        name = instance._descriptor_to_name(self)
        class_name = instance.__class__.__name__
        return f"Error with '{class_name}.{name}':"

    def finalize_and_validate_configuration(self, instance: Configurable) -> None:
        if self.required and instance._get_config(self) is None:
            name = instance._descriptor_to_name(self)
            prefix = self._error_prefix(instance)
            raise ValueError("{prefix} {name} is a required configuration setting, but no value was set")
