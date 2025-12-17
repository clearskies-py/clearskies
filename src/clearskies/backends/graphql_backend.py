from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from clearskies import configs, configurable, decorators, loggable
from clearskies.autodoc.schema import Integer as AutoDocInteger
from clearskies.autodoc.schema import Schema as AutoDocSchema
from clearskies.autodoc.schema import String as AutoDocString
from clearskies.backends.backend import Backend
from clearskies.clients import graphql_client as client
from clearskies.di import InjectableProperties, inject
from clearskies.functional.string import swap_casing

if TYPE_CHECKING:
    from clearskies import Column, Model
    from clearskies.query import Query


class GraphqlBackend(Backend, configurable.Configurable, InjectableProperties, loggable.Loggable):
    """
    Autonomous backend for integrating clearskies models with GraphQL APIs.

    Dynamically constructs GraphQL queries by introspecting the clearskies Model.
    Supports CRUD operations, pagination, filtering, and relationships.

    Configuration:
    - graphql_client: GraphqlClient instance (required)
    - root_field: Override the root field name (optional, defaults to model.destination_name())
    - pagination_style: "cursor" for Relay-style or "offset" for limit/offset (default: "cursor")
    - api_case: Case convention used by the GraphQL API (default: "camelCase")
    - model_case: Case convention used by clearskies models (default: "snake_case")
    - is_collection: Explicitly set if this resource is a collection (True) or singular (False/None=auto-detect)
    - include_relationships: Enable automatic relationship fetching (default: False for performance)
    - max_relationship_depth: Maximum depth for nested relationships (default: 2)
    - nested_relationships: Allow relationships within relationships (default: False)
    - relationship_limit: Default limit for HasMany/ManyToMany relationships (default: 10)
    - use_connection_for_relationships: Use connection pattern for collections (default: True)
    """

    # Tell clearskies that count() may not be reliable for all GraphQL APIs
    # This prevents clearskies from trying to call count() in situations where
    # it would fail (e.g., for relationship queries with incompatible filters)
    can_count = True

    """
    The GraphQL client instance used to execute queries.

    An instance of clearskies.clients.GraphqlClient that handles the connection to your GraphQL API.
    This is required for the backend to function. Example:

    ```python
    import clearskies

    class Project(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.GraphqlBackend(
            graphql_client=clearskies.clients.GraphqlClient(
                endpoint="https://api.example.com/graphql",
                authentication=clearskies.authentication.SecretBearer(
                    environment_key="API_TOKEN"
                )
            ),
            root_field="projects"
        )
        id = clearskies.columns.String()
        name = clearskies.columns.String()
    ```
    """
    graphql_client = configs.Any(default=None)

    """
    The name of the GraphQL client in the DI container.

    If you don't provide a graphql_client directly, the backend will look for a client
    registered in the dependency injection container with this name. Defaults to "graphql_client".
    """
    graphql_client_name = configs.String(default="graphql_client")

    """
    Override the root field name used in GraphQL queries.

    By default, the backend uses model.destination_name() converted to the API's case convention.
    Use this to explicitly set a different root field name. Example:

    ```python
    backend = clearskies.backends.GraphqlBackend(
        graphql_client=my_client,
        root_field="allProjects"  # Override default "projects"
    )
    ```
    """
    root_field = configs.String(default="")

    """
    The pagination strategy used by the GraphQL API.

    Supported values:
    - "cursor": Relay-style cursor pagination with pageInfo { endCursor, hasNextPage }
    - "offset": Traditional limit/offset pagination

    Defaults to "cursor" which is the most common pattern in GraphQL APIs.
    """
    pagination_style = configs.String(default="cursor")

    """
    The case convention used by the GraphQL API for field names.

    Common values: "camelCase", "snake_case", "PascalCase", "kebab-case"
    Defaults to "camelCase" which is the GraphQL standard.
    """
    api_case = configs.String(default="camelCase")

    """
    The case convention used by clearskies model column names.

    Common values: "snake_case", "camelCase", "PascalCase", "kebab-case"
    Defaults to "snake_case" which is the Python/clearskies standard.
    """
    model_case = configs.String(default="snake_case")

    """
    Explicitly set whether the resource is a collection or singular.

    Values:
    - None: Auto-detect based on field name patterns (default)
    - True: Resource is a collection (returns multiple items with pagination)
    - False: Resource is singular (returns a single object, like "currentUser")

    Auto-detection works for most cases, but you can override it if needed.
    """
    is_collection = configs.Boolean(default=None, required=False)

    """
    Maximum depth for nested relationship queries.

    Controls how deep the backend will traverse relationships when building GraphQL queries.
    For example, with max_relationship_depth=2:
    - Depth 0: Root model (Group)
    - Depth 1: First level relationships (Group.projects)
    - Depth 2: Second level relationships (Project.namespace)

    This prevents infinite recursion in circular relationships. Defaults to 2.
    """
    max_relationship_depth = configs.Integer(default=2)

    """
    Default limit for HasMany and ManyToMany relationship collections.

    When fetching related collections (e.g., projects for a group), this sets the maximum
    number of related records to fetch. Defaults to 10.

    Example:
    ```python
    backend = clearskies.backends.GraphqlBackend(
        graphql_client=my_client,
        relationship_limit=50  # Fetch up to 50 related items
    )
    ```
    """
    relationship_limit = configs.Integer(default=10)

    """
    Whether to use GraphQL connection pattern for relationship collections.

    When True, relationship queries use the connection pattern:
    ```graphql
    projects(first: 10) {
        nodes { id name }
        pageInfo { endCursor hasNextPage }
    }
    ```

    When False, expects direct arrays:
    ```graphql
    projects { id name }
    ```

    Defaults to True (Relay-style connections are the GraphQL standard).
    """
    use_connection_for_relationships = configs.Boolean(default=True)

    _client: client.GraphqlClient
    di = inject.Di()

    @decorators.parameters_to_properties
    def __init__(
        self,
        graphql_client: client.GraphqlClient | None = None,
        graphql_client_name: str = "graphql_client",
        root_field: str = "",
        pagination_style: str = "cursor",
        api_case: str = "camelCase",
        model_case: str = "snake_case",
        is_collection: bool | None = None,
        max_relationship_depth: int = 2,
        relationship_limit: int = 10,
        use_connection_for_relationships: bool = True,
    ):
        self.finalize_and_validate_configuration()

    @property
    def client(self) -> client.GraphqlClient:
        """
        Get the GraphQL client instance.

        Lazily creates or retrieves the GraphqlClient used to execute queries. If a graphql_client
        was provided during initialization, it's used directly. Otherwise, the client is retrieved
        from the dependency injection container using graphql_client_name.

        Returns:
            GraphqlClient: The configured GraphQL client instance for executing queries.
        """
        if hasattr(self, "_client"):
            return self._client

        if self.graphql_client:
            self._client = self.graphql_client
        else:
            self.logger.warning("No GraphQL client provided, creating default client.")
            self._client = inject.ByName(self.graphql_client_name)  # type: ignore[assignment]
        self._client.injectable_properties(self.di)
        return self._client

    def _model_to_api_name(self, model_name: str) -> str:
        """Convert a model field name to API field name."""
        return swap_casing(model_name, self.model_case, self.api_case)

    def _api_to_model_name(self, api_name: str) -> str:
        """Convert an API field name to model field name."""
        return swap_casing(api_name, self.api_case, self.model_case)

    def _get_root_field_name(self, model: "Model" | type["Model"]) -> str:
        """Get the root field name for GraphQL queries."""
        if self.root_field:
            return self.root_field
        # Use the model's destination name and convert to API case
        return swap_casing(model.destination_name(), self.model_case, self.api_case)

    def _is_relationship_column(self, column: "Column") -> bool:
        """
        Check if a column represents a relationship that needs N+1 optimization.

        Uses the wants_n_plus_one flag which is the official clearskies pattern
        for identifying relationship columns (same pattern used by CursorBackend).
        """
        # Primary detection: check the wants_n_plus_one flag
        if hasattr(column, "wants_n_plus_one") and column.wants_n_plus_one:
            return True

        # Fallback: class name inspection for backwards compatibility
        column_type = column.__class__.__name__
        return column_type in ["BelongsTo", "HasMany", "ManyToMany", "BelongsToId", "BelongsToModel"]

    def _get_relationship_model(self, column: "Column") -> type["Model"] | None:
        """
        Extract the related model class from a relationship column.

        Tries multiple strategies to find the related model.
        """
        column_type = column.__class__.__name__

        # Strategy 1: Check for parent_models_class config (BelongsTo, BelongsToId)
        if hasattr(column, "config"):
            model = column.config("parent_models_class")
            if model:
                return model  # type: ignore[return-value]

            # Strategy 2: Check for child_models_class config (HasMany)
            model = column.config("child_models_class")
            if model:
                return model  # type: ignore[return-value]

        # Strategy 3: For BelongsToModel, look up the corresponding BelongsToId column
        if column_type == "BelongsToModel":
            # BelongsToModel stores the belongs_to_id column name in belongs_to_column_name attribute
            if hasattr(column, "belongs_to_column_name"):
                belongs_to_id_column_name = column.belongs_to_column_name
                if belongs_to_id_column_name:
                    # Get the model columns and look up the BelongsToId column
                    model_columns = column.get_model_columns() if hasattr(column, "get_model_columns") else {}
                    belongs_to_id_column = model_columns.get(belongs_to_id_column_name)
                    if belongs_to_id_column:
                        # BelongsToId has parent_model_class attribute
                        if hasattr(belongs_to_id_column, "parent_model_class"):
                            model = belongs_to_id_column.parent_model_class
                            if model:
                                return model  # type: ignore[return-value]

        # Strategy 4: Check for model_class attribute
        if hasattr(column, "model_class") and column.model_class:
            # Make sure it's not the same as the parent model
            parent_columns = column.get_model_columns() if hasattr(column, "get_model_columns") else {}
            if parent_columns and column.model_class != type(parent_columns):
                return column.model_class  # type: ignore[return-value]

        # Could not determine relationship model
        return None

    def _build_relationship_field(self, column: "Column", depth: int) -> str:
        """
        Build a nested GraphQL field for a relationship column.

        Dispatches to specific builders based on relationship type.
        """
        column_type = column.__class__.__name__

        if column_type in ["BelongsTo", "BelongsToModel", "BelongsToId"]:
            return self._build_belongs_to_field(column, depth)
        elif column_type in ["HasMany", "ManyToMany"]:
            return self._build_has_many_field(column, depth)

        return ""

    def _build_belongs_to_field(self, column: "Column", depth: int) -> str:
        """
        Build a nested field for BelongsTo relationships (single parent).

        Pattern: Direct nested object
        Example: user { id name email }
        """
        related_model = self._get_relationship_model(column)
        if not related_model:
            return ""

        field_name = self._model_to_api_name(column.name)

        # Build fields for the related model
        # Always include relationships at depth + 1 (controlled by max_relationship_depth)
        related_fields = self._build_graphql_fields(related_model.get_columns(), depth=depth + 1)

        return f"{field_name} {{ {related_fields} }}"

    def _build_has_many_field(self, column: "Column", depth: int) -> str:
        """
        Build a nested field for HasMany relationships (collection of children).

        Pattern: Connection with nodes/edges or direct array
        Example: orders(first: 10) { nodes { id total } pageInfo { endCursor hasNextPage } }
        """
        related_model = self._get_relationship_model(column)
        if not related_model:
            return ""

        field_name = self._model_to_api_name(column.name)

        # Build fields for the related model
        # Recursion is controlled by max_relationship_depth
        related_fields = self._build_graphql_fields(
            related_model.get_columns(),
            depth=depth + 1,
        )

        # Use connection pattern or direct array based on configuration
        if self.use_connection_for_relationships:
            return f"""{field_name}(first: {self.relationship_limit}) {{
                nodes {{ {related_fields} }}
                pageInfo {{ endCursor hasNextPage }}
            }}"""
        else:
            return f"{field_name} {{ {related_fields} }}"

    def _build_nested_field_from_underscore(self, column_name: str) -> str:
        """
        Build a nested GraphQL field from double underscore notation.

        Converts clearskies' double underscore notation to GraphQL nested field syntax.

        Examples:
            "user__name" -> "user { name }"
            "project__owner__email" -> "project { owner { email } }"
            "order__customer__address__city" -> "order { customer { address { city } } }"

        Args:
            column_name: Column name with double underscores (e.g., "user__name")

        Returns:
            GraphQL nested field string
        """
        parts = column_name.split("__")
        if len(parts) < 2:
            # Not a nested field, shouldn't happen but handle gracefully
            return self._model_to_api_name(column_name)

        # Convert all parts to API case
        api_parts = [self._model_to_api_name(part) for part in parts]

        # Build nested structure from the inside out
        # Start with the innermost field (the actual value we want)
        result = api_parts[-1]

        # Wrap each level from right to left
        # e.g., ["user", "name"] -> "user { name }"
        # e.g., ["project", "owner", "email"] -> "project { owner { email } }"
        for i in range(len(api_parts) - 2, -1, -1):
            result = f"{api_parts[i]} {{ {result} }}"

        return result

    def _build_graphql_fields(self, columns: dict[str, "Column"], depth: int = 0) -> str:
        """
        Dynamically build GraphQL field selection from model columns.

        Handles nested relationships up to a certain depth to prevent infinite recursion.
        Automatically converts field names from model case to API case.

        ALWAYS includes relationships for columns with wants_n_plus_one=True, as per
        clearskies' standard backend behavior. This is not opt-in - it's automatic.

        Depth levels:
        - depth=0: Root model (e.g., Group)
        - depth=1: First level relationships (e.g., Group.projects)
        - depth=2: Second level relationships (e.g., Project.group)

        With max_relationship_depth=2, we include relationships at depth 0 and 1, but not at depth 2.
        """
        if depth >= self.max_relationship_depth:
            return "id"

        fields = []
        for name, column in columns.items():
            # Skip non-readable columns
            if not column.is_readable:
                continue

            # Handle relationship columns using the N+1 pattern
            # This is ALWAYS done for columns with wants_n_plus_one=True
            if self._is_relationship_column(column):
                # Only include relationships if we haven't reached the max depth
                # This prevents infinite recursion (Group → Project → Group → Project...)
                if depth < self.max_relationship_depth - 1:
                    # Generate nested GraphQL structure instead of SQL JOIN
                    nested_field = self._build_relationship_field(column, depth)
                    if nested_field:
                        fields.append(nested_field)
                continue

            # Handle double underscore notation (e.g., "user__name" -> nested query)
            # GraphQL natively supports nested field selection, so we can convert this easily
            if "__" in name:
                # Build nested GraphQL structure from double underscore notation
                # Example: "user__name" becomes "user { name }"
                # Example: "project__owner__email" becomes "project { owner { email } }"
                nested_field = self._build_nested_field_from_underscore(name)
                if nested_field:
                    fields.append(nested_field)
                continue

            # Convert model field name to API field name
            api_field_name = self._model_to_api_name(name)
            fields.append(api_field_name)

        return " ".join(fields) if fields else "id"

    def _is_singular_resource(self, root_field: str) -> bool:
        """
        Determine if a resource is singular (single object) or plural (collection).

        Singular resources (e.g., currentUser, viewer, me) return a single object.
        Plural resources (e.g., projects, users, items) return collections with pagination.

        This can be explicitly configured via the is_collection parameter, or auto-detected
        using common GraphQL naming patterns.
        """
        # If explicitly configured, use that
        if self.is_collection is not None:
            return not self.is_collection

        # Auto-detect using common GraphQL naming patterns
        root_lower = root_field.lower()

        # Common patterns for singular resources in various GraphQL APIs
        # (GitHub, GitLab, Shopify, etc.)
        singular_patterns = ["current", "viewer", "me", "my"]

        # Check if it starts with a singular pattern
        for pattern in singular_patterns:
            if root_lower.startswith(pattern):
                return True

        # If root_field ends with 's', it's likely plural (collection)
        # Exception: words ending in 'ss' (e.g., 'address', 'business')
        if root_field.endswith("s") and not root_field.endswith("ss"):
            return False

        # If uncertain, check against common singular words
        # Most GraphQL APIs use plural for collections, singular for single objects
        # Default to plural (collection) if ends with common singular patterns
        singular_endings = ["er", "or", "ion", "ment", "ness", "ship"]
        for ending in singular_endings:
            if root_lower.endswith(ending):
                return True

        # Final fallback: if it looks like a typical noun, assume singular
        # This is a safe default as it won't add pagination structure to non-paginated queries
        return True

    def _build_query(self, query: "Query") -> tuple[str, dict]:
        """
        Dynamically build a GraphQL query from a clearskies Query object.

        Returns: (query_string, variables_dict)
        """
        model = query.model_class
        root_field = self._get_root_field_name(model)
        columns = model.get_columns()

        # Build field selection
        fields = self._build_graphql_fields(columns)

        # Determine if this is a singular resource or a collection
        is_singular = self._is_singular_resource(root_field)

        # Build query arguments
        args_parts = []
        variables = {}
        variable_definitions = []

        # Handle filters (where conditions) - only for collections
        if not is_singular:
            for i, condition in enumerate(query.conditions):
                # Convert model column name to API field name
                api_column_name = self._model_to_api_name(condition.column_name)

                if condition.operator == "=":
                    value = condition.values[0]
                    column = columns.get(condition.column_name)

                    # Check if this is a Select/Enum column
                    # For enum types, pass the value directly in the query (not as a variable)
                    # This avoids GraphQL type mismatch issues with enum types
                    if column and column.__class__.__name__ == "Select":
                        # Pass enum value directly in the query without variables
                        args_parts.append(f"{api_column_name}: {value}")
                    else:
                        # Use variables for non-enum types
                        var_name = f"filter_{condition.column_name}_{i}"
                        args_parts.append(f"{api_column_name}: ${var_name}")

                        if isinstance(value, bool) or str(value).lower() in ("true", "false"):
                            variable_definitions.append(f"${var_name}: Boolean")
                            # Convert string 'true'/'false' to boolean
                            if isinstance(value, str):
                                variables[var_name] = value.lower() == "true"
                            else:
                                variables[var_name] = value
                        elif isinstance(value, int):
                            variable_definitions.append(f"${var_name}: Int")
                            variables[var_name] = int(value)  # type: ignore[assignment]
                        else:
                            variable_definitions.append(f"${var_name}: String")
                            variables[var_name] = str(value)  # type: ignore[assignment]
                elif condition.operator == "in" and len(condition.values) > 0:
                    var_name = f"filter_{condition.column_name}_in_{i}"
                    args_parts.append(f"{api_column_name}_in: ${var_name}")
                    variable_definitions.append(f"${var_name}: [String!]")
                    variables[var_name] = [str(v) for v in condition.values]  # type: ignore[assignment]

        # Handle pagination - only for collections
        if not is_singular:
            if self.pagination_style == "cursor":
                if "cursor" in query.pagination:
                    args_parts.append("after: $after")
                    variable_definitions.append("$after: String")
                    variables["after"] = str(query.pagination["cursor"])  # type: ignore[assignment]

                if query.limit:
                    args_parts.append("first: $first")
                    variable_definitions.append("$first: Int")
                    variables["first"] = int(query.limit)  # type: ignore[assignment]
            else:  # offset-based pagination
                if query.limit:
                    args_parts.append("limit: $limit")
                    variable_definitions.append("$limit: Int")
                    variables["limit"] = int(query.limit)  # type: ignore[assignment]

                if "start" in query.pagination:
                    args_parts.append("offset: $offset")
                    variable_definitions.append("$offset: Int")
                    variables["offset"] = int(query.pagination["start"])  # type: ignore[assignment]

        # Handle sorting - only for collections
        if not is_singular and query.sorts:
            sort = query.sorts[0]
            api_sort_column = self._model_to_api_name(sort.column_name)
            args_parts.append("sortBy: $sortBy")
            args_parts.append("sortDirection: $sortDirection")
            variable_definitions.append("$sortBy: String")
            variable_definitions.append("$sortDirection: String")
            variables["sortBy"] = api_sort_column  # type: ignore[assignment]
            variables["sortDirection"] = sort.direction.upper()  # type: ignore[assignment]

        # Build the query string
        args_str = f"({', '.join(args_parts)})" if args_parts else ""
        var_def_str = f"({', '.join(variable_definitions)})" if variable_definitions else ""

        # Build different query structures for singular vs plural resources
        if is_singular:
            # Singular resource - returns a single object directly
            query_str = f"""
            query GetRecords{var_def_str} {{
                {root_field}{args_str} {{
                    {fields}
                }}
            }}
            """
        elif self.pagination_style == "cursor":
            # Plural resource with cursor pagination - returns connection with nodes/pageInfo
            query_str = f"""
            query GetRecords{var_def_str} {{
                {root_field}{args_str} {{
                    nodes {{
                        {fields}
                    }}
                    pageInfo {{
                        endCursor
                        hasNextPage
                    }}
                }}
            }}
            """
        else:
            # Plural resource with offset pagination - returns array
            query_str = f"""
            query GetRecords{var_def_str} {{
                {root_field}{args_str} {{
                    {fields}
                }}
            }}
            """

        return query_str, variables

    def _extract_records(self, response: dict) -> list[dict]:
        # Extract records from nested GraphQL response
        # Support both {"data": {...}} and direct {...} responses
        data = response.get("data", response)
        records = data.get(self.root_field, [])
        # If the root field is a dict, try to unwrap one more level (for single-object queries)
        if records is None:
            return []
        if isinstance(records, dict):
            # If this dict has only scalar fields, wrap it in a list (single record)
            if not any(isinstance(v, (dict, list)) for v in records.values()):
                return [records]
            # If this dict has "nodes" or "edges", handle as before
            if "nodes" in records and isinstance(records["nodes"], list):
                return records["nodes"]
            if "edges" in records:
                # Relay-style connection
                return [edge["node"] for edge in records["edges"]]
            # Otherwise, return as a single record in a list
            return [records]
        return records

    def _map_relationship_data(self, record: dict, column: "Column", parent_model: "Model | None" = None) -> Any:
        """
        Map nested relationship data from GraphQL response to clearskies format.

        Returns raw dict data (not Model instances) to maintain separation between
        _data (raw values) and _transformed_data (processed values). The relationship
        columns handle transformation to Model instances when accessed.

        For BelongsTo relationships, returns a single dict.
        For HasMany/ManyToMany relationships, returns a list of dicts.
        """
        related_model = self._get_relationship_model(column)
        if not related_model:
            return None

        api_field_name = self._model_to_api_name(column.name)
        nested_data = record.get(api_field_name)

        if nested_data is None:
            return None

        column_type = column.__class__.__name__

        # BelongsTo: single object - return raw dict
        if column_type in ["BelongsTo", "BelongsToModel", "BelongsToId"]:
            if isinstance(nested_data, dict):
                # Map and return the raw dict data
                return self._map_record(nested_data, related_model.get_columns())
            return None

        # HasMany/ManyToMany: collection - return list of raw dicts
        if column_type in ["HasMany", "ManyToMany"]:
            # Extract nodes from connection pattern
            nodes = []
            if isinstance(nested_data, dict) and "nodes" in nested_data:
                nodes = nested_data["nodes"] if isinstance(nested_data["nodes"], list) else []
            elif isinstance(nested_data, list):
                nodes = nested_data

            # Map each node to a raw dict (NOT Model instances)
            child_dicts = []
            for node in nodes:
                child_data = self._map_record(node, related_model.get_columns())
                child_dicts.append(child_data)

            return child_dicts

        return None

    def _map_record(self, record: dict, columns: dict, parent_model: "Model | None" = None) -> dict:
        """
        Map GraphQL response record to clearskies model format.

        Handles case conversion from API format to model format.
        Flattens nested GraphQL records to clearskies flat dict.
        Supports nested relationship data mapping.
        """
        flat = {}
        for name, col in columns.items():
            # Handle relationship columns
            if self._is_relationship_column(col):
                relationship_data = self._map_relationship_data(record, col, parent_model)
                if relationship_data is not None:
                    flat[name] = relationship_data
                continue

            # Handle nested field notation (e.g., "user__name")
            if "__" in name:
                value = record
                for part in name.split("__"):
                    api_part = self._model_to_api_name(part)
                    if isinstance(value, dict):
                        value = value.get(api_part)  # type: ignore[assignment]
                    else:
                        value = None
                flat[name] = value
            else:
                # Simple field - convert name and extract value
                api_field_name = self._model_to_api_name(name)
                flat[name] = record.get(api_field_name)  # type: ignore[assignment]

        return flat

    def _build_mutation(
        self, operation: str, model: "Model", data: dict[str, Any], id: int | str | None = None
    ) -> tuple[str, dict]:
        """
        Dynamically build a GraphQL mutation.

        Args:
            operation: "create", "update", or "delete"
            model: The clearskies Model
            data: Data to mutate
            id: Record ID (for update/delete)

        Returns: (mutation_string, variables_dict)
        """
        root_field = self._get_root_field_name(model)
        mutation_name = f"{operation}{root_field.capitalize()}"
        columns = model.get_columns()
        fields = self._build_graphql_fields(columns)

        variables = {}
        variable_definitions = []
        args_parts = []

        if operation in ["update", "delete"]:
            variable_definitions.append("$id: ID!")
            args_parts.append("id: $id")
            variables["id"] = str(id)

        if operation in ["create", "update"]:
            # Build input object - convert model field names to API field names
            for key, value in data.items():
                if key in columns and columns[key].is_writeable:
                    api_field_name = self._model_to_api_name(key)
                    var_name = f"input_{key}"
                    variable_definitions.append(f"${var_name}: String")
                    args_parts.append(f"{api_field_name}: ${var_name}")
                    variables[var_name] = str(value) if value is not None else None  # type: ignore[assignment]

        var_def_str = f"({', '.join(variable_definitions)})" if variable_definitions else ""
        args_str = f"({', '.join(args_parts)})" if args_parts else ""

        if operation == "delete":
            mutation_str = f"""
            mutation {mutation_name}{var_def_str} {{
                {operation}{root_field.capitalize()}{args_str} {{
                    success
                }}
            }}
            """
        else:
            mutation_str = f"""
            mutation {mutation_name}{var_def_str} {{
                {operation}{root_field.capitalize()}{args_str} {{
                    {fields}
                }}
            }}
            """

        return mutation_str, variables

    def update(self, id: int | str, data: dict[str, Any], model: "Model") -> dict[str, Any]:
        """Update a record via GraphQL mutation."""
        mutation_str, variables = self._build_mutation("update", model, data, id)
        try:
            response = self.client.execute(mutation_str, variable_values=variables)
            records = self._extract_records(response)
            if not records:
                raise Exception("No data returned from update mutation")
            return self._map_record(records[0], model.get_columns())
        except Exception as e:
            raise Exception(f"GraphQL update failed: {e}")

    def create(self, data: dict[str, Any], model: "Model") -> dict[str, Any]:
        """Create a record via GraphQL mutation."""
        mutation_str, variables = self._build_mutation("create", model, data)
        try:
            response = self.client.execute(mutation_str, variable_values=variables)
            records = self._extract_records(response)
            if not records:
                raise Exception("No data returned from create mutation")
            return self._map_record(records[0], model.get_columns())
        except Exception as e:
            raise Exception(f"GraphQL create failed: {e}")

    def delete(self, id: int | str, model: "Model") -> bool:
        """Delete a record via GraphQL mutation."""
        mutation_str, variables = self._build_mutation("delete", model, {}, id)
        try:
            self.client.execute(mutation_str, variable_values=variables)
            return True
        except Exception as e:
            raise Exception(f"GraphQL delete failed: {e}")

    def count(self, query: "Query") -> int:
        """
        Return the count of records matching the query.

        Attempts to use a dedicated count field or falls back to counting returned records.
        """
        # Try to build a count query
        model = query.model_class
        root_field = self._get_root_field_name(model)

        # First, try a dedicated count query
        count_query = f"""
        query {{
            {root_field}Count
        }}
        """
        try:
            response = self.client.execute(count_query)
            data = response.get("data", {})
            if f"{root_field}Count" in data:
                return int(data[f"{root_field}Count"])
        except Exception:
            # Count query not supported, fall back to fetching and counting
            pass

        # Fallback: fetch records and count them
        query_str, variables = self._build_query(query)
        try:
            response = self.client.execute(query_str, variable_values=variables)
            return len(self._extract_records(response))
        except Exception as e:
            raise Exception(f"GraphQL count failed: {e}")

    def records(self, query: "Query", next_page_data: dict[str, str | int] | None = None) -> list[dict[str, Any]]:
        """
        Fetch records matching the query.

        Handles pagination data to enable fetching additional pages.
        Supports pre-loaded records from relationship columns.
        """
        # Check if query has pre-loaded records (from relationship columns)
        self.logger.debug(f"Checking for pre-loaded records. hasattr: {hasattr(query, '_pre_loaded_records')}")
        self.logger.debug(f"Query attributes: {dir(query)}")
        if hasattr(query, "_pre_loaded_records"):
            self.logger.debug("Using pre-loaded relationship data, skipping GraphQL query")
            pre_loaded = query._pre_loaded_records  # type: ignore[attr-defined]
            # Clear the pre-loaded data to avoid reuse
            delattr(query, "_pre_loaded_records")
            return pre_loaded

        query_str, variables = self._build_query(query)
        self.logger.info(f"GraphQL Query:\n{query_str}")
        self.logger.info(f"Variables: {variables}")
        try:
            response = self.client.execute(query_str, variable_values=variables)
            self.logger.debug(f"GraphQL response: {response}")

            # Extract records from response
            records = self._extract_records(response)
            self.logger.debug(f"Extracted {len(records)} records from GraphQL response.")

            # Map records to clearskies format
            mapped = [self._map_record(r, query.model_class.get_columns()) for r in records]
            self.logger.debug(f"Mapped records: {mapped}")

            # Handle pagination
            if isinstance(next_page_data, dict):
                if self.pagination_style == "cursor":
                    # Extract cursor from pageInfo
                    data = response.get("data", response)
                    root_field = self._get_root_field_name(query.model_class)
                    root_data = data.get(root_field, {})

                    if "pageInfo" in root_data:
                        page_info = root_data["pageInfo"]
                        if page_info.get("hasNextPage"):
                            next_page_data["cursor"] = str(page_info.get("endCursor", ""))  # type: ignore[assignment]
                else:
                    # Offset-based pagination
                    limit = query.limit
                    start = query.pagination.get("start", 0)
                    if limit and len(records) == limit:
                        next_page_data["start"] = int(start) + int(limit)

            return mapped
        except Exception as e:
            self.logger.error(f"GraphQL records failed: {e}")
            raise Exception(f"GraphQL records failed: {e}")

    def validate_pagination_data(self, data: dict[str, Any], case_mapping: Callable[[str], str]) -> str:
        """Validate pagination data based on the configured pagination style."""
        allowed_keys = set(self.allowed_pagination_keys())
        extra_keys = set(data.keys()) - allowed_keys

        if extra_keys:
            return f"Invalid pagination key(s): '{','.join(extra_keys)}'. Allowed keys: {', '.join(allowed_keys)}"

        if self.pagination_style == "cursor":
            if data and "cursor" not in data:
                key_name = case_mapping("cursor")
                return f"You must specify '{key_name}' when setting pagination"
        else:  # offset
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

    def allowed_pagination_keys(self) -> list[str]:
        """Return allowed pagination keys based on style."""
        if self.pagination_style == "cursor":
            return ["cursor"]
        return ["start"]

    def documentation_pagination_next_page_response(self, case_mapping: Callable) -> list[Any]:
        """Return pagination documentation for responses."""
        if self.pagination_style == "cursor":
            return [AutoDocString(case_mapping("cursor"), example="eyJpZCI6IjEyMyJ9")]
        return [AutoDocInteger(case_mapping("start"), example=0)]

    def documentation_pagination_next_page_example(self, case_mapping: Callable) -> dict[str, Any]:
        """Return example pagination data."""
        if self.pagination_style == "cursor":
            return {case_mapping("cursor"): "eyJpZCI6IjEyMyJ9"}
        return {case_mapping("start"): 0}

    def documentation_pagination_parameters(self, case_mapping: Callable) -> list[tuple[AutoDocSchema, str]]:
        """Return pagination parameter documentation."""
        if self.pagination_style == "cursor":
            return [
                (
                    AutoDocString(case_mapping("cursor"), example="eyJpZCI6IjEyMyJ9"),
                    "A cursor token to fetch the next page of results",
                )
            ]
        return [
            (
                AutoDocInteger(case_mapping("start"), example=0),
                "The zero-indexed record number to start listing results from",
            )
        ]
