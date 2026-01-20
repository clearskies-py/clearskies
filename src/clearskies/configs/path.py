from __future__ import annotations

from pathlib import Path as PathType

from clearskies.configs import config


class Path(config.Config):
    def __init__(self, required=False, default=None, check_for_existence: bool = True):
        self.required = required
        self.default = default
        self.check_for_existence = check_for_existence

    def __set__(self, instance, value: PathType | str) -> None:
        if not isinstance(value, (PathType, str)):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requires a Path."
            )
        if isinstance(value, str):
            value = PathType(value)
        if self.check_for_existence and not value.exists():
            error_prefix = self._error_prefix(instance)
            raise ValueError(f"{error_prefix} path '{value}' does not exist")

        instance._set_config(self, value)

    def __get__(self, instance, parent) -> PathType:
        if not instance:
            return self  # type: ignore
        return instance._get_config(self)

    def finalize_and_validate_configuration(self, instance):
        # The Configurable class sets the default value directly in _config,
        # bypassing __set__. We need to convert string values to Path objects here.
        try:
            current_value = instance._get_config(self)
            if isinstance(current_value, str):
                path_value = PathType(current_value)
                if self.check_for_existence and not path_value.exists():
                    error_prefix = self._error_prefix(instance)
                    raise ValueError(f"{error_prefix} path '{path_value}' does not exist")
                instance._set_config(self, path_value)
        except KeyError:
            pass
