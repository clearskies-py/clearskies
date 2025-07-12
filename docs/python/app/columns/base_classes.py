from __future__ import annotations
from typing import overload, Self, TYPE_CHECKING
from types import ModuleType

import clearskies

if TYPE_CHECKING:
    from clearskies import Model


class BaseClasses(clearskies.columns.HasMany):
    def __init__(
        self,
        readable_child_column_names: list[str] = [],
    ):
        self.foreign_column_name = "type"
        self.readable_child_column_names = readable_child_column_names

    def finalize_configuration(self, model_class, name) -> None:
        self.child_model_class = model_class
        super().finalize_configuration(model_class, name)

    def __get__(self, model, cls):
        if model is None:
            self.model_class = cls
            return self  # type:  ignore

        # this makes sure we're initialized
        if "name" not in self._config:
            model.get_columns()

        bases = []
        for cls in model.type.__bases__:
            bases.append(model.model(model.backend.unpack(cls, model.module)))

        return bases
