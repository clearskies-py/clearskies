from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

from clearskies import loggable
from clearskies.autodoc.schema import Schema as AutoDocSchema

if TYPE_CHECKING:
    from clearskies import Column, Model
    from clearskies.query import Query
    from clearskies.query.result import (
        CountQueryResult,
        RecordQueryResult,
        RecordsQueryResult,
        SuccessQueryResult,
    )


class Backend(ABC, loggable.Loggable):
    """
    Connecting models to their data since 2020!.

    The backend system acts as a flexible layer between models and their data sources.  By changing the backend attached to a model,
    you change where the model fetches and saves data.  This might be a database, an in-memory data store, a dynamodb table,
    an API, and more.  This allows you to interact with a variety of data sources with the models acting as a standardized API.
    Since endpoints also rely on the models for their functionality, this means that you can easily build API endpoints and
    more for a variety of data sources with a minimal amount of code.

    Of course, not all data sources support all functionality present in the model.  Therefore, you do still need to have
    a fair understanding of how your data sources work.
    """

    supports_n_plus_one = False
    can_count = True

    @abstractmethod
    def update(self, id: int | str, data: dict[str, Any], model: Model) -> RecordQueryResult:
        """Update the record with the given id with the information from the data dictionary."""
        pass

    @abstractmethod
    def create(self, data: dict[str, Any], model: Model) -> RecordQueryResult:
        """Create a record with the information from the data dictionary."""
        pass

    @abstractmethod
    def delete(self, id: int | str, model: Model) -> SuccessQueryResult:
        """Delete the record with the given id."""
        pass

    @abstractmethod
    def count(self, query: Query) -> CountQueryResult:
        """Return the number of records which match the given query configuration."""
        pass

    @abstractmethod
    def records(self, query: Query) -> RecordsQueryResult:
        """
        Return a list of records that match the given query configuration.

        The QueryResult includes next_page_data for pagination information.
        """
        pass

    @abstractmethod
    def validate_pagination_data(self, data: dict[str, Any], case_mapping: Callable[[str], str]) -> str:
        """
        Check if the given dictionary is valid pagination data for the background.

        Return a string with an error message, or an empty string if the data is valid
        """
        pass

    @abstractmethod
    def allowed_pagination_keys(self) -> list[str]:
        """
        Return the list of allowed keys in the pagination kwargs for the backend.

        It must always return keys in snake_case so that the auto casing system can
        adjust on the front-end for consistency.
        """
        pass

    @abstractmethod
    def documentation_pagination_next_page_response(self, case_mapping: Callable) -> list[Any]:
        """
        Return a list of autodoc schema objects.

        It will describe the contents of the `next_page` dictionary
        in the pagination section of the response
        """
        pass

    @abstractmethod
    def documentation_pagination_parameters(self, case_mapping: Callable) -> list[tuple[AutoDocSchema, str]]:
        """
        Return a list of autodoc schema objects describing the allowed input keys to set pagination.

        It should return a list of tuples, with each tuple corresponding to an input key.
        The first element in the tuple should be the schema, and the second should be the description.
        """
        pass

    @abstractmethod
    def documentation_pagination_next_page_example(self, case_mapping: Callable) -> dict[str, Any]:
        """
        Return an example for next page documentation.

        Returns an example (as a simple dictionary) of what the next_page data in the pagination response
        should look like
        """
        pass

    def extract_count_from_response(
        self,
        response_headers: dict[str, str] | None = None,
        response_data: Any = None,
    ) -> tuple[int | None, int | None]:
        """
        Extract count information from backend response.

        This hook allows backends to extract total count and total pages from
        response metadata (e.g., HTTP headers, response envelope data). Override
        in backends that can extract count from response headers/data, such as
        API backends with X-Total-Count headers.

        This enables count caching in QueryResult - when records() returns,
        the count can be cached from the response headers so that a subsequent
        count() call doesn't need to make a separate request.

        Returns a tuple of (total_count, total_pages). Both values will be None
        if count is not available.

        Example implementation for an API backend:

        ```python
        def extract_count_from_response(
            self,
            response_headers: dict[str, str] | None = None,
            response_data: Any = None,
        ) -> tuple[int | None, int | None]:
            if not response_headers:
                return (None, None)
            total_count = response_headers.get("X-Total-Count")
            total_pages = response_headers.get("X-Total-Pages")
            if total_count is not None:
                return (int(total_count), int(total_pages) if total_pages else None)
            return (None, None)
        ```
        """
        return (None, None)

    def column_from_backend(self, column: Column, value: Any) -> Any:
        """
        Manage transformations from the backend.

        The idea with this (and `column_to_backend`) is that the transformations to
        and from the backend are mostly determined by the column type - integer, string,
        date, etc...  However, there are cases where these are also backend specific: a datetime
        column may be serialized different ways for different databases, a JSON column must be
        serialized for a database but won't be serialized for an API call, etc...  Therefore
        we mostly just let the column handle this, but we want the backend to be in charge
        in case it needs to make changes.
        """
        return column.from_backend(value)

    def column_to_backend(self, column: Column, backend_data: dict[str, Any]) -> dict[str, Any]:
        """
        Manage transformations to the backend.

        The idea with this (and `column_from_backend`) is that the transformations to
        and from the backend are mostly determined by the column type - integer, string,
        date, etc...  However, there are cases where these are also backend specific: a datetime
        column may be serialized different ways for different databases, a JSON column must be
        serialized for a database but won't be serialized for an API call, etc...  Therefore
        we mostly just let the column handle this, but we want the backend to be in charge
        in case it needs to make changes.
        """
        return column.to_backend(backend_data)
