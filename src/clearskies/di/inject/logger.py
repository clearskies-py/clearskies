from __future__ import annotations

import logging
from typing import Self, overload

from clearskies.di.injectable import Injectable


class Logger(Injectable):
    def __init__(self, cache: bool = False):
        self.cache = cache

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> logging.Logger: ...
    def __get__(self, instance, parent):
        if instance is None:
            return self
        self.initiated_guard(instance)
        return logging.getLogger(parent.__name__)
