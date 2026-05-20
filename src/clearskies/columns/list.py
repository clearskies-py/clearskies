from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable, Self, overload

from clearskies import configs, decorators
from clearskies.column import Column

if TYPE_CHECKING:
    from clearskies import Model, typing


class List(Column):
    """
    A column to store a list of values, optionally restricted to a specific item type.

    ```python
    import clearskies


    class MyModel(clearskies.Model):
        backend = clearskies.backends.MemoryBackend()
        id_column_name = "id"

        id = clearskies.columns.Uuid()
        tags = clearskies.columns.List()
        scores = clearskies.columns.List(value_type=int)


    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.Create(
            MyModel,
            writeable_column_names=["tags", "scores"],
            readable_column_names=["id", "tags", "scores"],
        ),
        classes=[MyModel],
    )
    wsgi()
    ```

    And when invoked:

    ```bash
    $ curl 'http://localhost:8080' -d '{"tags":["python","clearskies"],"scores":[10,20,30]}' | jq
    {
        "status": "success",
        "error": "",
        "data": {
            "id": "63cbd5e7-a198-4424-bd35-3890075a2a5e",
            "tags": ["python", "clearskies"],
            "scores": [10, 20, 30]
        },
        "pagination": {},
        "input_errors": {}
    }
    ```

    Use ``value_type`` to restrict all items to a single type or a tuple of types:

    ```python
    # only strings allowed
    tags = clearskies.columns.List(value_type=str)

    # strings or integers allowed
    mixed = clearskies.columns.List(value_type=(str, int))
    ```

    When a ``value_type`` is set, any API input that contains an item of the wrong
    type will be rejected with a ``400 input_errors`` response.

    Note: there is no attempt to validate the internal *shape* of dict items.
    """

    setable = configs.Any(default=None)
    default = configs.Any(default=None)
    value_type: configs.Type[type | tuple[type, ...]] = configs.Type(default=None)
    is_searchable = configs.Boolean(default=False)
    _descriptor_config_map = None

    @decorators.parameters_to_properties
    def __init__(
        self,
        default: list[Any] | None = None,
        setable: list[Any] | Callable[..., list[Any]] | None = None,
        is_readable: bool = True,
        is_writeable: bool = True,
        is_temporary: bool = False,
        validators: typing.validator | list[typing.validator] = [],
        value_type: type | tuple[type, ...] | None = None,
        on_change_pre_save: typing.action | list[typing.action] = [],
        on_change_post_save: typing.action | list[typing.action] = [],
        on_change_save_finished: typing.action | list[typing.action] = [],
        created_by_source_type: str = "",
        created_by_source_key: str = "",
        created_by_source_strict: bool = True,
    ):
        pass

    @overload
    def __get__(self, instance: None, cls: type[Model]) -> Self:
        pass

    @overload
    def __get__(self, instance: Model, cls: type[Model]) -> list[Any] | None:
        pass

    def __get__(self, instance, cls) -> Self | list[Any] | None:
        return super().__get__(instance, cls)

    def __set__(self, instance, value: list[Any] | None) -> None:
        # this makes sure we're initialized
        if not self._config or "name" not in self._config:
            instance.get_columns()

        instance._next_data[self.name] = value

    def _type_name(self) -> str:
        """Return a human-readable name for the configured ``value_type``."""
        t = self.value_type
        if t is None:
            raise ValueError("_type_name() must only be called when value_type is set")
        if isinstance(t, tuple):
            return " | ".join(x.__name__ for x in t)
        return t.__name__

    def from_backend(self, value: str | list[Any] | None) -> list[Any] | None:
        # Already a parsed list — return as-is; type enforcement is the API boundary's job.
        if isinstance(value, list):
            return value

        # Treat falsy non-list values (None, "") as absent.
        if not value:
            return None

        # Deserialise from a JSON string stored by the backend.
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None

        if not isinstance(parsed, list):
            return None

        return parsed

    def to_backend(self, data: dict[str, Any]) -> dict[str, Any]:
        if self.name not in data or data[self.name] is None:
            return data

        value = data[self.name]
        # Serialise to a JSON string unless it is already one (idempotent).
        return {**data, self.name: value if isinstance(value, str) else json.dumps(value)}

    def force_value_from_input(self, value: Any) -> Any:
        """Coerce a JSON string from a query param or CLI arg into a Python list."""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else value
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    def input_error_for_value(self, value: Any, operator: str | None = None) -> str:
        if not isinstance(value, list):
            return "value must be a list"

        if self.value_type:
            type_name = self._type_name()
            for item in value:
                if not isinstance(item, self.value_type):
                    return f"all items must be of type {type_name}, but got an item of type {item.__class__.__name__}"

        return ""
