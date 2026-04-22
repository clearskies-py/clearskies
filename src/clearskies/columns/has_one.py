from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, overload

from clearskies.autodoc.schema import Object as AutoDocObject
from clearskies.columns.has_many import ChildModel, HasMany

if TYPE_CHECKING:
    from clearskies import Model
    from clearskies.autodoc.schema import Schema as AutoDocSchema


class HasOne(HasMany[ChildModel]):
    """
    This operates exactly like the HasMany relationship, except it assumes there is only ever one child.

    The only real difference between this and HasMany is that the HasMany column type will return a list
    of models, while this returns the first model.
    """

    _descriptor_config_map = None

    @overload
    def __get__(self, model: None, cls: type[Model]) -> Self:
        pass

    @overload
    def __get__(self, model: Model, cls: type[Model]) -> ChildModel:
        pass

    def __get__(self, model, cls):  # type: ignore[override]
        if model is None:
            self.model_class = cls
            return self

        return super().__get__(model, cls).first()

    def __set__(self, model: Model, value: Model) -> None:
        raise ValueError(
            f"Attempt to set a value to {model.__class__.__name__}.{self.name}: this is not allowed because it is a HasOne column, which is not writeable."
        )

    def to_json(self, model: Model) -> dict[str, Any]:
        child = getattr(model, self.name)
        columns = self.child_columns
        child_id_column_name = self.child_model_class.id_column_name

        # If the child is empty (no data), return None
        if not child:
            return {self.name: None}

        json = columns[child_id_column_name].to_json(child)
        for column_name in self.readable_child_column_names or []:
            json = {
                **json,
                **columns[column_name].to_json(child),
            }
        return {self.name: json}

    def documentation(
        self, name: str | None = None, example: str | None = None, value: str | None = None
    ) -> list[AutoDocSchema]:
        columns = self.child_columns
        child_id_column_name = self.child_model_class.id_column_name
        child_properties: list[AutoDocSchema] = [*columns[child_id_column_name].documentation()]

        for column_name in self.readable_child_column_names or []:
            child_properties.extend(columns[column_name].documentation())

        return [
            AutoDocObject(
                name if name is not None else self.name,
                child_properties,
            )
        ]
