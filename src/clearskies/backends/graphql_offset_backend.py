from __future__ import annotations

from typing import Any, Callable

from clearskies.autodoc.schema import Integer as AutoDocInteger
from clearskies.autodoc.schema import Schema as AutoDocSchema
from clearskies.backends.graphql_backend import GraphqlBackend
from clearskies.query import Query


class GraphqlOffsetBackend(GraphqlBackend):
    """Manage GraphQL interactions with a server that uses offset pagination instead of cursor-based pagination."""

    def validate_pagination_data(self, data: dict[str, Any], case_mapping: Callable[[str], str]) -> str:
        """Validate pagination data based on the configured pagination style."""
        allowed_keys = set(self.allowed_pagination_keys())
        extra_keys = set(data.keys()) - allowed_keys

        if extra_keys:
            return f"Invalid pagination key(s): '{','.join(extra_keys)}'. Allowed keys: {', '.join(allowed_keys)}"

        if data and "start" not in data:
            key_name = case_mapping("start")
            return f"You must specify '{key_name}' when setting pagination"
        if "start" in data:
            try:
                int(data["start"])
            except Exception:
                key_name = case_mapping("start")
                return f"Invalid pagination data: '{key_name}' must be a number"

        return ""

    def query_for_collection_resource(
        self,
        root_field: str,
        args_parts: list[str],
        variables: dict[str, Any],
        variable_definitions: list[str],
        fields: str,
    ) -> str:
        """Return the query string to fetch a collection of resources from the server."""
        args_str = f"({', '.join(args_parts)})" if args_parts else ""
        var_def_str = f"({', '.join(variable_definitions)})" if variable_definitions else ""

        return f"""
        query GetRecords{var_def_str} {{
            {root_field}{args_str} {{
                {fields}
            }}
        }}
        """

    def add_pagination(
        self,
        query: Query,
        args_parts: list[str],
        variables: dict[str, Any],
        variable_definitions: list[str],
    ) -> None:
        """
        Add the necessary variables to the query to account for offset-based pagination.

        Note: there is no return value because all args are passed by reference and modified in-place.
        Note: this is always called, so pagination may not be set.
        """
        if "start" in query.pagination:
            args_parts.append("offset: $offset")
            variable_definitions.append("$offset: Int")
            variables["offset"] = int(query.pagination["start"])

        if not query.limit:
            return

        args_parts.append("limit: $limit")
        variable_definitions.append("$limit: Int")
        variables["limit"] = int(query.limit)

    def extract_next_page_data(self, query: Query, response: Any, records: list[Any]) -> dict[str, str | int] | None:
        limit = query.limit
        start = query.pagination.get("start", 0)
        if limit and len(records) == limit:
            return {"start": int(start) + int(limit)}

        return None

    def allowed_pagination_keys(self) -> list[str]:
        """Return allowed pagination keys based on style."""
        return ["start"]

    def documentation_pagination_next_page_response(self, case_mapping: Callable) -> list[Any]:
        """Return pagination documentation for responses."""
        return [AutoDocInteger(case_mapping("start"), example=0)]

    def documentation_pagination_next_page_example(self, case_mapping: Callable) -> dict[str, Any]:
        """Return example pagination data."""
        return {case_mapping("start"): 0}

    def documentation_pagination_parameters(self, case_mapping: Callable) -> list[tuple[AutoDocSchema, str]]:
        """Return pagination parameter documentation."""
        return [
            (
                AutoDocInteger(case_mapping("start"), example=0),
                "The zero-indexed record number to start listing results from",
            )
        ]
