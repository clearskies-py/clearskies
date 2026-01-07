from __future__ import annotations

import types

from clearskies.di.injectable import Injectable


class Subprocess(Injectable):
    def __init__(self, cache: bool = True):
        self.cache = cache

    def __get__(self, instance, parent) -> types.ModuleType:
        if instance is None:
            return self  # type: ignore
        self.initiated_guard(instance)
        return self._di.build_from_name("subprocess", cache=self.cache)  # type: ignore
