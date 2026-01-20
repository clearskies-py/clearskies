from __future__ import annotations

from pathlib import Path as PathType

from clearskies.configs import config


class Path(config.Config):
    def __set__(self, instance, value: PathType | str):
        if not isinstance(value, (PathType, str)):
            error_prefix = self._error_prefix(instance)
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requires a Path."
            )
        if isinstance(value, str):
            value = PathType(value)
        if not value.exists():
            error_prefix = self._error_prefix(instance)
            raise ValueError(f"{error_prefix} path '{value}' does not exist")

        instance._set_config(self, value)

    def __get__(self, instance, parent) -> PathType:
        if not instance:
            return self  # type: ignore
        return instance._get_config(self)
