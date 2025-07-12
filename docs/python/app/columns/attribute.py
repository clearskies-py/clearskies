from __future__ import annotations
from typing import overload, Self, TYPE_CHECKING, Callable
from types import ModuleType

import clearskies

if TYPE_CHECKING:
    from clearskies import Model


class Attribute(clearskies.columns.HasMany):
    def __init__(
        self,
        child_model_class,
        readable_child_column_names: list[str] = [],
        filter: Callable | None = None,
    ):
        self.filter = filter
        super().__init__(
            child_model_class,
            foreign_column_name="parent_class",
            readable_child_column_names=readable_child_column_names,
        )

    def __get__(self, model, cls):
        if model is None:
            self.model_class = cls
            return self  # type:  ignore

        # this makes sure we're initialized
        if "name" not in self._config:
            model.get_columns()

        attributes = self.child_model.where(self.child_model_class.parent_class.equals(model.type))
        if self.filter:
            return list(filter(self.filter, attributes))[0]

        return attributes[0]
