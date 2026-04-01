from __future__ import annotations

from types import ModuleType
from typing import Self, overload

from clearskies.di.injectable import Injectable


class AkeylessSDK(Injectable):
    def __init__(self, cache: bool = True):
        self.cache = cache

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> ModuleType: ...
    def __get__(self, instance, parent):
        if instance is None:
            return self
        self.initiated_guard(instance)
        return self._di.build_from_name("akeyless_sdk", cache=self.cache)
