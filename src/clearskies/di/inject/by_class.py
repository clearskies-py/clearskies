from __future__ import annotations

import inspect
from typing import Any

from clearskies.di.injectable import Injectable
from clearskies.functional import validations


class ByClass(Injectable):
    def __init__(self, cls: type, cache: bool = True):
        if not isinstance(cls, type):
            raise TypeError(
                f"I expected a class for the first argument to clearskies.di.inject.ByClass, but I received an object of type '{cls.__class__.__name__}' instead."
            )
        self.cls = cls
        self.cache = cache

    def __get__(self, instance, parent) -> Any:
        if instance is None:
            return self

        self.initiated_guard(instance)
        if validations.is_model_class_reference(self.cls):
            class_reference = self.cls() if inspect.isclass(self.cls) else self.cls
            cls = class_reference.get_model_class()
        else:
            cls = self.cls
        if cls in self._di._class_overrides_by_class:
            return self._di.build_class(self._di._class_overrides_by_class[cls], cache=self.cache)
        return self._di.build_class(cls, cache=self.cache)
