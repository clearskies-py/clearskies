from __future__ import annotations
from typing import overload, Self, TYPE_CHECKING
from types import ModuleType

import clearskies

if TYPE_CHECKING:
    from clearskies import Model


class ModuleClasses(clearskies.columns.HasMany):
    def __init__(
        self,
        child_model_class,
        readable_child_column_names: list[str] = [],
    ):
        super().__init__(
            child_model_class,
            foreign_column_name="module",
            readable_child_column_names=readable_child_column_names,
        )

    def __get__(self, model, cls):
        if model is None:
            self.model_class = cls
            return self  # type:  ignore

        # this makes sure we're initialized
        if "name" not in self._config:
            model.get_columns()

        return self.child_model.where(cls.module.equals(model.module))
