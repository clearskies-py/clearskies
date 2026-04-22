from __future__ import annotations

import types
from typing import Self, overload

from clearskies.di.injectable import Injectable


class Subprocess(Injectable):
    def __init__(self, cache: bool = True):
        self.cache = cache

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> types.ModuleType: ...
    def __get__(self, instance, parent):
        if instance is None:
            return self
        self.initiated_guard(instance)
        return self._di.build_from_name("subprocess", cache=self.cache)
