from __future__ import annotations

from pathlib import Path as PathType
from typing import TYPE_CHECKING, overload

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.configurable import Configurable


class PathList(config.Config):
    """
    A configuration property that holds a list of filesystem paths.

    Accepts a list of str or pathlib.Path objects. Each entry is stored as a
    pathlib.Path. When the value is read, non-existent paths are silently filtered out.

    Example:
    ```python
    from clearskies import configs
    from clearskies.configurable import Configurable


    class MyClass(Configurable):
        sql = configs.PathList(default=["sql"])
    ```
    """

    def __init__(self, required: bool = False, default: list[str | PathType] | None = None):
        self.required = required
        self.default = default

    def __set__(self, instance: Configurable, value: list[str | PathType]) -> None:
        if value is None:
            return
        if not isinstance(value, list):
            error_prefix = self._error_prefix(instance)
            raise TypeError(f"{error_prefix} expected a list but received '{value.__class__.__name__}'")
        paths = []
        for index, item in enumerate(value):
            if not isinstance(item, (str, PathType)):
                error_prefix = self._error_prefix(instance)
                raise TypeError(
                    f"{error_prefix} item #{index + 1} must be a str or Path, not '{item.__class__.__name__}'"
                )
            paths.append(PathType(item))
        instance._set_config(self, paths)

    @overload
    def __get__(self, instance: None, parent: type) -> PathList: ...

    @overload
    def __get__(self, instance: Configurable, parent: type) -> list[PathType]: ...

    def __get__(self, instance: Configurable | None, parent: type) -> PathList | list[PathType]:
        if instance is None:
            return self
        raw: list[PathType | str] = instance._get_config(self)
        if raw is None:
            return []
        # The default value bypasses __set__ so entries may still be plain strings.
        # Convert to Path before filtering for existence.
        return [p for item in raw if (p := PathType(item)).exists()]
