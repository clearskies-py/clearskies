from __future__ import annotations

from types import ModuleType

from clearskies.di.injectable import Injectable


class AkeylessSDK(Injectable):
    def __init__(self, cache: bool = True):
        self.cache = cache

    def __get__(self, instance, parent) -> ModuleType:
        if instance is None:
            return self  # type: ignore
        self.initiated_guard(instance)
        return self._di.build_from_name("akeyless_sdk", cache=self.cache)
