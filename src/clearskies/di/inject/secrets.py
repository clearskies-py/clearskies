from __future__ import annotations

from typing import TYPE_CHECKING

from clearskies.di.injectable import Injectable

if TYPE_CHECKING:
    from clearskies.secrets.secrets import Secrets as SecretsHelper


class Secrets(Injectable):
    def __init__(self, cache: bool = True):
        self.cache = cache

    def __get__(self, instance, parent) -> SecretsHelper:
        if instance is None:
            return self  # type: ignore
        self.initiated_guard(instance)
        return self._di.build_from_name("secrets", cache=self.cache)
