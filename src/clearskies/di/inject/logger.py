from __future__ import annotations

import logging

from clearskies.di.injectable import Injectable


class Logger(Injectable):
    def __init__(self, cache: bool = False):
        self.cache = cache

    def __get__(self, instance, parent) -> logging.Logger:
        if instance is None:
            return self  # type: ignore
        self.initiated_guard(instance)
        return logging.getLogger(parent.__name__)
