from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clearskies import configs, decorators
from clearskies.column import Column
from clearskies.columns.has_many import HasMany

if TYPE_CHECKING:
    from clearskies import Model, typing


class Audit(HasMany):
    """
    Enables auditing for a model.

    Specify the audit class to use and attach this column to your model. Everytime the model is created/updated/deleted,
    the audit class will record the action and the changes.  Your audit model must have the following columns:

    | Name        | type     |
    |-------------|----------|
    | class_name  | str      |
    | resource_id | str      |
    | action      | str      |
    | data        | json     |
    | created_at  | created  |

    The names are not currently adjustable.

     1. Class is a string that records the name of the class that the action happened for.  This allows you to use
        the same audit class for multiple, different, resources.
     2. resource_id is the id of the record which the audit entry is for.
     3. Action is the actual action taken (create/update/delete)
     4. Data is a serialized record of what columns in the record were changed (both their previous and new values)
     5. The time the audit record was created

    Here's an example:

    ```
    #!/usr/bin/env python

    import clearskies


    class PersonHistory(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()

        id = clearskies.columns.Uuid()
        class_name = clearskies.columns.String()
        resource_id = clearskies.columns.String()
        action = clearskies.columns.String()
        data = clearskies.columns.Json()
        created_at = clearskies.columns.Created(date_format="%Y-%m-%d %H:%M:%S.%f")


    class Person(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()

        id = clearskies.columns.Uuid()
        name = clearskies.columns.String()
        age = clearskies.columns.Integer()
        history = clearskies.columns.Audit(audit_model_class=PersonHistory)


    def test_audit(persons: Person):
        bob = persons.create({"name": "Bob", "age": 30})
        bob.save({"age": 31})
        bob.save({"age": 32})
        bob.delete()

        return bob.history.sort_by("created_at", "asc")


    cli = clearskies.contexts.Cli(
        clearskies.endpoints.Callable(
            test_audit,
            model_class=PersonHistory,
            return_records=True,
            readable_column_names=["id", "action", "data", "created_at"],
        ),
        classes=[Person, PersonHistory],
    )

    if __name__ == "__main__":
        cli()
    ```

    And if you invoke this you will get back:

    ```
    {
        "status": "success",
        "error": "",
        "data": [
            {
                "id": "25eae3d9-d64b-4819-9e31-70e1d4d34945",
                "action": "create",
                "data": {"name": "Bob", "age": 30, "id": "145c7cf2-3fc6-41c8-b3b2-f68eb2b08b03"},
                "created_at": "2025-12-04T12:14:42.540108+00:00",
            },
            {
                "id": "c8dea383-ae1d-4e25-a58e-d4ebdf2fb4f9",
                "action": "update",
                "data": {"from": {"age": 30}, "to": {"age": 31}},
                "created_at": "2025-12-04T12:14:42.540384+00:00",
            },
            {
                "id": "5e1f3067-a45a-4463-8a66-3b92d47a8863",
                "action": "update",
                "data": {"from": {"age": 31}, "to": {"age": 32}},
                "created_at": "2025-12-04T12:14:42.540595+00:00",
            },
            {
                "id": "44179d35-9abb-4117-803c-ec87bb58adb5",
                "action": "delete",
                "data": {"name": "Bob", "age": 32, "id": "145c7cf2-3fc6-41c8-b3b2-f68eb2b08b03"},
                "created_at": "2025-12-04T12:14:42.540747+00:00",
            },
        ],
        "pagination": {"number_results": 4, "limit": 0, "next_page": {}},
        "input_errors": {},
    }
    ```

    """

    """ The model class for the destination that will store the audit data. """
    audit_model_class = configs.ModelClass(required=True)

    """
    A list of columns that shouldn't be copied into the audit record.

    To be clear, these are columns from the model class that the audit column is attached to.
    If only excluded columns are updated then no audit record will be created.
    """
    exclude_columns = configs.ModelColumns(default=[])

    """
    A list of columns that should be masked when copied into the audit record.

    With masked columns a generic value is placed in the audit record (e.g. XXXXX) which denotes that
    the column was changed, but it does not record either old or new values.
    """
    mask_columns = configs.ModelColumns(default=[])

    """ Columns from the child table that should be included when converting this column to JSON. """
    readable_child_column_names = configs.ReadableModelColumns(
        "audit_model_class", default=["resource_id", "action", "data", "created_at"]
    )

    """
    Since this column is always populated automatically, it is never directly writeable.
    """
    is_writeable = configs.Boolean(default=False)
    is_searchable = configs.Boolean(default=False)
    _descriptor_config_map = None
    _parent_columns: dict[str, Column] | None

    @decorators.parameters_to_properties
    def __init__(
        self,
        audit_model_class,
        exclude_columns: list[str] = [],
        mask_columns: list[str] = [],
        foreign_column_name: str | None = None,
        readable_child_column_names: list[str] = [],
        where: typing.condition | list[typing.condition] = [],
        default: str | None = None,
        is_readable: bool = True,
        is_temporary: bool = False,
        on_change_pre_save: typing.action | list[typing.action] = [],
        on_change_post_save: typing.action | list[typing.action] = [],
        on_change_save_finished: typing.action | list[typing.action] = [],
    ):
        self.child_model_class = self.audit_model_class
        self.foreign_column_name = "resource_id"

    def save_finished(self, model: Model):
        super().save_finished(model)
        old_data: dict[str, Any] = model._previous_data
        new_data: dict[str, Any] = model.get_raw_data()
        exclude_columns = self.exclude_columns
        mask_columns = self.mask_columns
        model_columns = self.get_model_columns()

        if not old_data:
            create_data: dict[str, Any] = {}
            for key in new_data.keys():
                if key in self.exclude_columns or key == self.name:
                    continue
                if key in model_columns:
                    column_data = model_columns[key].to_json(model)
                else:
                    column_data = {key: new_data[key]}

                create_data = {
                    **create_data,
                    **column_data,
                }
                if key in mask_columns and key in create_data:
                    create_data[key] = "****"
            self.record(model, "create", data=create_data)
            return

        # note that this is fairly simple logic to get started.  It's not going to detect changes that happen
        # in other "tables".  For instance, disconnecting a record by deleting an entry in a many-to-many relationship
        # won't be picked up by this.
        old_model = model.empty()
        old_model._data = old_data
        from_data: dict[str, Any] = {}
        to_data: dict[str, Any] = {}
        for column, new_value in new_data.items():
            if column in exclude_columns or column not in old_data or column == self.name:
                continue
            if old_data[column] == new_value:
                continue
            from_data = {
                **from_data,
                **(
                    model_columns[column].to_json(old_model)
                    if column in model_columns
                    else {column: old_data.get(column)}
                ),
            }
            to_data = {
                **to_data,
                **(
                    model_columns[column].to_json(model)
                    if column in model_columns
                    else {column: model._data.get(column)}
                ),
            }
            if column in mask_columns and column in to_data:
                to_data[column] = "****"
                from_data[column] = "****"
        if not from_data and not to_data:
            return

        self.record(
            model,
            "update",
            data={
                "from": from_data,
                "to": to_data,
            },
        )

    def post_delete(self, model: Model) -> None:
        super().post_delete(model)
        exclude_columns = self.exclude_columns
        model_columns = self.get_model_columns()
        mask_columns = self.mask_columns

        final_data: dict[str, Any] = {}
        for key in model._data.keys():
            if key in exclude_columns or key == self.name:
                continue
            final_data = {
                **final_data,
                **(model_columns[key].to_json(model) if key in model_columns else {key: model.get_raw_data().get(key)}),
            }

        for key in mask_columns:
            if key not in final_data:
                continue
            final_data[key] = "****"

        self.child_model.create(
            {
                "class_name": self.model_class.__name__,
                "resource_id": getattr(model, self.model_class.id_column_name),
                "action": "delete",
                "data": final_data,
            }
        )

    @property
    def parent_columns(self) -> dict[str, Column]:
        if self._parent_columns == None:
            self._parent_columns = self.di.build(self.model_class, cache=True).columns()
        return self._parent_columns  # type: ignore[return-value]

    def record(self, model, action, data=None, record_data=None):
        audit_data = {
            "class_name": self.model_class.__name__,
            "resource_id": getattr(model, self.model_class.id_column_name),
            "action": action,
        }
        if data is not None:
            audit_data["data"] = data
        if record_data is not None:
            audit_data = {
                **audit_data,
                **record_data,
            }

        self.child_model.create(audit_data)

    def __get__(self, model, cls):
        if model is None:
            self.model_class = cls
            return self  # type:  ignore

        return super().__get__(model, cls).where(f"class_name={self.model_class.__name__}")
