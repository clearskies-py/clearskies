from __future__ import annotations

from typing import Any

from clearskies.di.injectable import Injectable


class Di(Injectable):
    def __init__(self):
        pass

    def __get__(self, instance, parent) -> Any:
        if instance is None:
            return self  # type: ignore
        self.initiated_guard(instance)
        return self._di
