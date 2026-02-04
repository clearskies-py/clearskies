from typing import TYPE_CHECKING, Any, Callable

from clearskies.autodoc.schema import Schema as AutoDocSchema
from clearskies.backends.backend import Backend
from clearskies.di import inject
from clearskies.query import Condition, Query
from clearskies.query.result import RecordQueryResult, RecordsQueryResult, SuccessQueryResult

if TYPE_CHECKING:
    from clearskies import Model


class SecretsBackend(Backend):
    """
    Fetch and store data from a secret provider.

    ## Installing Dependencies

    Clearskies uses Akeyless by default to manage the secrets.
    This is not installed by default, but is a named extra that you can install when needed via:

    ```bash
    pip install clear-skies[secrets]
    ```
    """

    """The secrets instance."""
    secrets = inject.Secrets()

    can_count: bool = False

    def __init__(
        self,
        can_create: bool | None = True,
        can_update: bool | None = True,
        can_delete: bool | None = True,
        can_query: bool | None = True,
    ):
        # Only pass permission flags to parent if they are explicitly set (not None)
        # This allows the parent's default values (True) to be used when not specified
        parent_kwargs = {}
        if can_create is not None:
            parent_kwargs["can_create"] = can_create
        if can_update is not None:
            parent_kwargs["can_update"] = can_update
        if can_delete is not None:
            parent_kwargs["can_delete"] = can_delete
        if can_query is not None:
            parent_kwargs["can_query"] = can_query
        super().__init__(**parent_kwargs)

    def check_query(self, query: Query) -> None:
        if not query.conditions:
            raise KeyError(f"You must search by an id when using the secrets backend.")

    def update(self, id: str, data: dict[str, Any], model: Model) -> RecordQueryResult:  # type: ignore[override]
        """
        Update the record with the given id with the information from the data dictionary.

        Updates each key in the data dictionary as a separate secret in the secrets provider.
        The secrets are stored under a folder path based on the model's table name and the
        record id.

        The result contains the updated record accessible via the `record` property:

        ```python
        result = backend.update("user-123", {"api_key": "new-key"}, user_model)
        updated_record = result.record  # {"id": "user-123", "api_key": "new-key", ...}
        ```
        """
        folder_path = self._make_folder_path(model, id)
        for key, value in data.items():
            if key == model.id_column_name:
                continue
            self.secrets.update(f"{folder_path}{key}", value)

        # and now query again to fetch the updated record.
        records_response = self.records(Query(model.__class__, conditions=[Condition(f"{model.id_column_name}={id}")]))
        return RecordQueryResult(record=records_response.data[0])

    def create(self, data: dict[str, Any], model: Model) -> RecordQueryResult:
        """
        Create a record with the information from the data dictionary.

        Creates secrets in the secrets provider for each key in the data dictionary.
        The id column must be provided in the data dictionary since the secrets backend
        cannot auto-generate ids.

        The result contains the created record accessible via the `record` property:

        ```python
        result = backend.create({"id": "user-123", "api_key": "secret"}, user_model)
        new_record = result.record  # {"id": "user-123", "api_key": "secret"}
        ```
        """
        if not model.id_column_name in data:
            raise ValueError(
                f"You must provide '{model.id_column_name}' when creating a record with the secrets backend"
            )
        return self.update(data[model.id_column_name], data, model)

    def delete(self, id: str, model: Model) -> SuccessQueryResult:  # type: ignore[override]
        """
        Delete the record with the given id.

        Note: This operation is not yet implemented and always returns success without
        actually deleting any secrets. Full implementation would require deleting all
        secrets under the record's folder path.

        The result indicates success via the `success` property:

        ```python
        result = backend.delete("user-123", user_model)
        assert result.success  # True (but no actual deletion occurs)
        ```
        """
        return SuccessQueryResult()

    def records(self, query: Query) -> RecordsQueryResult:
        """
        Return a list of records that match the given query configuration.

        Fetches secrets from the secrets provider based on the query conditions. The query
        must include a condition on the id column using the equals operator. All secrets
        under the record's folder path are retrieved and combined into a single record.

        The result contains the records accessible via the `records` property:

        ```python
        result = backend.records(query)
        for record in result.records:
            print(record["api_key"])
        ```
        """
        self.check_query(query)
        for condition in query.conditions:
            if condition.operator != "=":
                raise ValueError(
                    f"I'm not very smart and only know how to search with the equals operator, but I received a condition of {condition.parsed}.  If you need to support this, you'll have to extend the ApiBackend and overwrite the build_records_request method."
                )
            if condition.column_name == query.model_class.id_column_name:
                id = condition.values[0]
                break
        if id is None:
            raise ValueError(f"You must search by '{query.model_class.id_column_name}' when using the secrets backend")

        folder_path = self._make_folder_path(query.model_class, id)
        data = {query.model_class.id_column_name: id}
        for path in self.secrets.list_secrets(folder_path):
            data[path[len(folder_path) :]] = self.secrets.get(path)
        return RecordsQueryResult(records=[data])

    def _make_folder_path(self, model, id):
        return model.table_name().rstrip("/") + "/" + id.strip("/") + "/"

    def validate_pagination_data(self, data: dict[str, Any], case_mapping: Callable[[str], str]) -> str:
        return ""

    def allowed_pagination_keys(self) -> list[str]:
        return []

    def documentation_pagination_next_page_response(self, case_mapping: Callable) -> list[Any]:
        return []

    def documentation_pagination_parameters(self, case_mapping: Callable) -> list[tuple[AutoDocSchema, str]]:
        return []

    def documentation_pagination_next_page_example(self, case_mapping: Callable) -> dict[str, Any]:
        return {}
