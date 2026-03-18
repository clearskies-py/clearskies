from __future__ import annotations

from typing import TYPE_CHECKING, Self, overload

from clearskies.di.injectable import Injectable

if TYPE_CHECKING:
    from clearskies.input_outputs.input_output import InputOutput as InputOuputDependency


class InputOutput(Injectable):
    def __init__(self):
        pass

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> InputOuputDependency: ...
    def __get__(self, instance, parent):
        if instance is None:
            return self
        self.initiated_guard(instance)
        return self._di.build_from_name("input_output", cache=True)
