from __future__ import annotations

import datetime
from typing import Self, overload

from clearskies.di.injectable import Injectable


class Utcnow(Injectable):
    def __init__(self, cache: bool = False):
        self.cache = cache

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> datetime.datetime: ...
    def __get__(self, instance, parent):
        if instance is None:
            return self
        self.initiated_guard(instance)
        return self._di.build_from_name("utcnow", cache=self.cache)
