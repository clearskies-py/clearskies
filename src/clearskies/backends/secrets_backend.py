from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from clearskies.autodoc.schema import Schema as AutoDocSchema
from clearskies.backends.backend import Backend
from clearskies.di import InjectableProperties, inject
from clearskies.query import Condition, Query
from clearskies.query.result import CountQueryResult, RecordQueryResult, RecordsQueryResult, SuccessQueryResult

if TYPE_CHECKING:
    from clearskies import Model


class SecretsBackend(Backend, InjectableProperties):
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

    def update(self, id: int | str, data: dict[str, Any], model: Model) -> RecordQueryResult:
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
            self.secrets.upsert(f"{folder_path}{key}", value)

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

    def delete(self, id: int | str, model: Model) -> SuccessQueryResult:
        """
        Delete the record with the given id.

        Deletes every secret under the record's folder path.

        The result indicates success via the `success` property:

        ```python
        result = backend.delete("user-123", user_model)
        assert result.success
        ```
        """
        folder_path = self._make_folder_path(model, id)
        for path in self.secrets.list_secrets(folder_path):
            self.secrets.delete(path)
        return SuccessQueryResult()

    def count(self, query: Query) -> CountQueryResult:
        """Return the number of records matching the query: 0 or 1, since the query must be by id."""
        return CountQueryResult(count=len(self.records(query).records))

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
        id = None
        filters = {}
        for condition in query.conditions:
            if condition.operator != "=":
                raise ValueError(
                    f"I'm not very smart and only know how to search with the equals operator, but I received a condition of {condition.parsed}.  If you need to support this, you'll have to extend the ApiBackend and overwrite the build_records_request method."
                )
            if condition.column_name == query.model_class.id_column_name:
                id = condition.values[0]
            else:
                filters[condition.column_name] = condition.values[0]
        if id is None:
            raise ValueError(f"You must search by '{query.model_class.id_column_name}' when using the secrets backend")

        folder_path = self._make_folder_path(query.model_class, id)
        paths = self.secrets.list_secrets(folder_path)
        if not paths:
            return RecordsQueryResult(records=[])
        data = {query.model_class.id_column_name: id}
        for path in paths:
            data[path.rsplit("/", 1)[-1]] = self.secrets.get(path)
        # secrets are stored as strings, so compare the other conditions as strings too
        if any(str(data.get(column_name)) != str(value) for (column_name, value) in filters.items()):
            return RecordsQueryResult(records=[])
        return RecordsQueryResult(records=[data])

    def _make_folder_path(self, model, id):
        id = str(id)
        # the id is one segment of the secret path, so it must not be able to point anywhere else
        if not id.strip() or "/" in id or id in (".", ".."):
            raise ValueError(f"Invalid id '{id}' for the secrets backend: it cannot be empty or contain '/'")
        return model.destination_name().rstrip("/") + "/" + id + "/"

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
