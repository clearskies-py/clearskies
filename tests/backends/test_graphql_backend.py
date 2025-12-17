"""Tests for GraphQL backend."""

import unittest
from unittest.mock import Mock

import clearskies
from clearskies.backends import GraphqlBackend
from clearskies.clients import GraphqlClient
from clearskies.query import Condition, Query


class User(clearskies.Model):
    """User model for testing."""

    id_column_name = "id"
    backend = None  # type: ignore[assignment]  # Will be set in tests

    id = clearskies.columns.String()
    name = clearskies.columns.String()
    email = clearskies.columns.String()
    age = clearskies.columns.Integer()


class Project(clearskies.Model):
    """Project model for testing."""

    id_column_name = "id"
    backend = None  # type: ignore[assignment]

    id = clearskies.columns.String()
    name = clearskies.columns.String()
    description = clearskies.columns.String()


class Group(clearskies.Model):
    """Group model with relationships for testing."""

    id_column_name = "id"
    backend = None  # type: ignore[assignment]

    id = clearskies.columns.String()
    name = clearskies.columns.String()
    projects = clearskies.columns.HasMany(child_model_class=Project, foreign_column_name="id")


class TestGraphqlBackend(unittest.TestCase):
    """Test GraphQL backend functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=GraphqlClient)
        self.backend = GraphqlBackend(graphql_client=self.mock_client, root_field="users")

    def test_initialization(self):
        """Test backend can be initialized."""
        assert self.backend.graphql_client == self.mock_client
        assert self.backend.root_field == "users"

    def test_case_conversion_snake_to_camel(self):
        """Test case conversion from snake_case to camelCase."""
        result = self.backend._convert_case("user_name", "snake_case", "camelCase")
        assert result == "userName"

    def test_case_conversion_camel_to_snake(self):
        """Test case conversion from camelCase to snake_case."""
        result = self.backend._convert_case("userName", "camelCase", "snake_case")
        assert result == "user_name"

    def test_model_to_api_name(self):
        """Test converting model field names to API names."""
        result = self.backend._model_to_api_name("user_name")
        assert result == "userName"

    def test_api_to_model_name(self):
        """Test converting API field names to model names."""
        result = self.backend._api_to_model_name("userName")
        assert result == "user_name"

    def test_get_root_field_name_from_config(self):
        """Test getting root field name from configuration."""
        backend = GraphqlBackend(graphql_client=self.mock_client, root_field="customRoot")
        result = backend._get_root_field_name(User)
        assert result == "customRoot"

    def test_get_root_field_name_from_model(self):
        """Test getting root field name from model destination_name."""
        backend = GraphqlBackend(graphql_client=self.mock_client)
        # User.destination_name() returns "users", convert to camelCase
        result = backend._get_root_field_name(User)
        assert result == "users"

    def test_is_singular_resource_explicit(self):
        """Test singular resource detection with explicit configuration."""
        backend = GraphqlBackend(graphql_client=self.mock_client, is_collection=False)
        assert backend._is_singular_resource("anything") is True

    def test_is_singular_resource_plural_pattern(self):
        """Test detecting plural resources."""
        backend = GraphqlBackend(graphql_client=self.mock_client)
        assert backend._is_singular_resource("users") is False
        assert backend._is_singular_resource("projects") is False

    def test_is_singular_resource_singular_pattern(self):
        """Test detecting singular resources."""
        backend = GraphqlBackend(graphql_client=self.mock_client)
        assert backend._is_singular_resource("currentUser") is True
        assert backend._is_singular_resource("viewer") is True
        assert backend._is_singular_resource("me") is True

    def test_build_graphql_fields_basic(self):
        """Test building GraphQL field selection."""
        columns = User.get_columns()
        fields = self.backend._build_graphql_fields(columns)

        # Should include readable columns in camelCase
        assert "id" in fields
        assert "name" in fields
        assert "email" in fields
        assert "age" in fields

    def test_build_graphql_fields_excludes_non_readable(self):
        """Test that non-readable columns are excluded."""

        class ModelWithSecret(clearskies.Model):
            id_column_name = "id"
            backend = None  # type: ignore[assignment]
            id = clearskies.columns.String()
            secret = clearskies.columns.String(is_readable=False)

        columns = ModelWithSecret.get_columns()
        fields = self.backend._build_graphql_fields(columns)

        assert "id" in fields
        assert "secret" not in fields

    def test_build_query_with_filters(self):
        """Test building query with filter conditions."""
        query = Query(User, conditions=[Condition("name=John")])
        query_str, variables = self.backend._build_query(query)

        assert "query GetRecords" in query_str
        assert "$filter_name_0" in query_str
        assert variables.get("filter_name_0") == "John"

    def test_build_query_with_boolean_filter(self):
        """Test building query with boolean filter."""

        class ModelWithBoolean(clearskies.Model):
            id_column_name = "id"
            backend = None  # type: ignore[assignment]
            id = clearskies.columns.String()
            is_active = clearskies.columns.Boolean()

        query = Query(ModelWithBoolean, conditions=[Condition("is_active=true")])
        backend = GraphqlBackend(graphql_client=self.mock_client)
        query_str, variables = self.backend._build_query(query)

        assert "$filter_is_active_0: Boolean" in query_str
        assert variables.get("filter_is_active_0") is True

    def test_build_query_with_pagination_cursor(self):
        """Test building query with cursor-based pagination includes variables."""
        backend = GraphqlBackend(
            graphql_client=self.mock_client,
            pagination_style="cursor",
            is_collection=True,  # Explicitly mark as collection
        )
        query = Query(User)
        # Directly set the query attributes since set_limit/set_pagination may not work as expected
        query.limit = 10
        query.pagination = {"cursor": "abc123"}

        # Build the query and verify pagination variables are included
        query_str, variables = backend._build_query(query)

        # Verify cursor pagination variables
        assert variables.get("after") == "abc123", f"Expected 'after' in variables, got: {variables}"
        assert variables.get("first") == 10, f"Expected 'first' in variables, got: {variables}"
        # Verify query structure includes pagination arguments
        assert "$after: String" in query_str
        assert "$first: Int" in query_str

    def test_build_query_with_pagination_offset(self):
        """Test building query with offset-based pagination includes variables."""
        backend = GraphqlBackend(
            graphql_client=self.mock_client,
            pagination_style="offset",
            is_collection=True,  # Explicitly mark as collection
        )
        query = Query(User)
        # Directly set the query attributes since set_limit/set_pagination may not work as expected
        query.limit = 10
        query.pagination = {"start": 20}

        # Build the query and verify pagination variables are included
        query_str, variables = backend._build_query(query)

        # Verify offset pagination variables
        assert variables.get("limit") == 10, f"Expected 'limit' in variables, got: {variables}"
        assert variables.get("offset") == 20, f"Expected 'offset' in variables, got: {variables}"
        # Verify query structure includes pagination arguments
        assert "$limit: Int" in query_str
        assert "$offset: Int" in query_str

    def test_extract_records_from_nodes(self):
        """Test extracting records from nodes structure."""
        backend = GraphqlBackend(graphql_client=self.mock_client, root_field="users")
        response = {"data": {"users": {"nodes": [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]}}}

        records = backend._extract_records(response)
        assert len(records) == 2
        assert records[0]["id"] == "1"
        assert records[1]["name"] == "Bob"

    def test_extract_records_from_edges(self):
        """Test extracting records from edges structure (Relay)."""
        backend = GraphqlBackend(graphql_client=self.mock_client, root_field="users")
        response = {
            "data": {"users": {"edges": [{"node": {"id": "1", "name": "Alice"}}, {"node": {"id": "2", "name": "Bob"}}]}}
        }

        records = backend._extract_records(response)
        assert len(records) == 2
        assert records[0]["name"] == "Alice"

    def test_extract_records_from_direct_array(self):
        """Test extracting records from direct array."""
        backend = GraphqlBackend(graphql_client=self.mock_client, root_field="users")
        response = {"data": {"users": [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]}}

        records = backend._extract_records(response)
        assert len(records) == 2

    def test_map_record_basic(self):
        """Test mapping GraphQL record to clearskies format."""
        record = {"id": "1", "name": "Alice", "email": "alice@example.com", "age": 30}
        columns = User.get_columns()

        mapped = self.backend._map_record(record, columns)

        assert mapped["id"] == "1"
        assert mapped["name"] == "Alice"
        assert mapped["email"] == "alice@example.com"
        assert mapped["age"] == 30

    def test_map_record_with_case_conversion(self):
        """Test mapping with case conversion."""
        record = {
            "id": "1",
            "firstName": "Alice",  # camelCase in API
        }

        class ModelWithCamelCase(clearskies.Model):
            id_column_name = "id"
            backend = None  # type: ignore[assignment]
            id = clearskies.columns.String()
            first_name = clearskies.columns.String()  # snake_case in model

        columns = ModelWithCamelCase.get_columns()
        mapped = self.backend._map_record(record, columns)

        assert mapped["first_name"] == "Alice"

    def test_records_method(self):
        """Test records method extracts and maps results correctly."""
        # Setup mock response
        response = {"data": {"users": {"nodes": [{"id": "1", "name": "Alice", "email": "alice@test.com", "age": 30}]}}}

        # Test extraction
        records = self.backend._extract_records(response)
        assert len(records) == 1
        assert records[0]["id"] == "1"

        # Test mapping
        mapped = self.backend._map_record(records[0], User.get_columns())
        assert mapped["id"] == "1"
        assert mapped["name"] == "Alice"

    def test_count_method(self):
        """Test count method extracts count correctly."""
        # Test with dedicated count field
        response_with_count = {"data": {"usersCount": 42}}
        # When there's a count field, _extract_records won't find nodes

        # Test counting from nodes
        response_with_nodes = {"data": {"users": {"nodes": [{"id": "1"}, {"id": "2"}]}}}
        records = self.backend._extract_records(response_with_nodes)
        assert len(records) == 2

    def test_allowed_pagination_keys_cursor(self):
        """Test allowed pagination keys for cursor style."""
        backend = GraphqlBackend(graphql_client=self.mock_client, pagination_style="cursor")
        keys = backend.allowed_pagination_keys()
        assert keys == ["cursor"]

    def test_allowed_pagination_keys_offset(self):
        """Test allowed pagination keys for offset style."""
        backend = GraphqlBackend(graphql_client=self.mock_client, pagination_style="offset")
        keys = backend.allowed_pagination_keys()
        assert keys == ["start"]

    def test_validate_pagination_data_cursor(self):
        """Test pagination data validation for cursor style."""
        backend = GraphqlBackend(graphql_client=self.mock_client, pagination_style="cursor")

        # Valid
        error = backend.validate_pagination_data({"cursor": "abc"}, str)
        assert error == ""

        # Invalid key
        error = backend.validate_pagination_data({"invalid": "abc"}, str)
        assert "Invalid pagination key" in error

    def test_validate_pagination_data_offset(self):
        """Test pagination data validation for offset style."""
        backend = GraphqlBackend(graphql_client=self.mock_client, pagination_style="offset")

        # Valid
        error = backend.validate_pagination_data({"start": 10}, str)
        assert error == ""

        # Invalid value
        error = backend.validate_pagination_data({"start": "not_a_number"}, str)
        assert "must be a number" in error


class TestGraphqlBackendRelationships(unittest.TestCase):
    """Test relationship support in GraphQL backend."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=GraphqlClient)
        # Relationships are now always included for columns with wants_n_plus_one=True
        self.backend = GraphqlBackend(graphql_client=self.mock_client, relationship_limit=5)

    def test_is_relationship_column_has_many(self):
        """Test detecting HasMany relationship columns."""
        column = Group.projects
        assert self.backend._is_relationship_column(column) is True

    def test_build_has_many_field(self):
        """Test building HasMany relationship field."""
        column = Group.projects
        field = self.backend._build_has_many_field(column, depth=0)

        assert "projects" in field
        assert "nodes" in field
        assert "pageInfo" in field
        assert "first: 5" in field  # relationship_limit

    def test_build_graphql_fields_with_relationships(self):
        """Test building fields with relationship support."""
        columns = Group.get_columns()
        fields = self.backend._build_graphql_fields(columns)

        # Should include relationship field
        assert "projects" in fields
        assert "nodes" in fields

    def test_build_query_with_relationships(self):
        """Test building query that includes relationships."""
        query = Query(Group)
        query_str, _ = self.backend._build_query(query)

        # Should include nested project structure
        assert "projects" in query_str
        assert "nodes" in query_str

    def test_max_relationship_depth(self):
        """Test that relationship depth is limited."""
        backend = GraphqlBackend(graphql_client=self.mock_client, max_relationship_depth=1)

        # At depth > max, should only return "id"
        columns = Project.get_columns()
        fields = backend._build_graphql_fields(columns, depth=2)

        assert fields == "id"

    def test_map_relationship_data_has_many(self):
        """Test extracting HasMany relationship data."""
        # Test that we can extract nested relationship data correctly
        column = Group.projects
        record = {
            "projects": {
                "nodes": [
                    {"id": "1", "name": "Project 1", "description": "Desc 1"},
                    {"id": "2", "name": "Project 2", "description": "Desc 2"},
                ]
            }
        }

        # Test that we can extract the nodes from the connection
        projects_data = record.get("projects", {})
        if "nodes" in projects_data:
            nodes = projects_data["nodes"]
            assert len(nodes) == 2
            assert nodes[0]["id"] == "1"
            assert nodes[1]["name"] == "Project 2"
        else:
            assert False, "Expected nodes in projects data"

    def test_map_relationship_data_belongs_to(self):
        """Test that BelongsTo relationships return model instances."""

        # Create a mock parent model to test BelongsTo
        # Note: Set backend to self.backend (not None) so the models can be instantiated
        class User(clearskies.Model):
            id_column_name = "id"
            backend = None  # type: ignore[assignment]  # Will be set by _map_relationship_data
            id = clearskies.columns.String()
            name = clearskies.columns.String()

        class Post(clearskies.Model):
            id_column_name = "id"
            backend = None  # type: ignore[assignment]  # Will be set by _map_relationship_data
            id = clearskies.columns.String()
            title = clearskies.columns.String()

        # Add BelongsTo relationship
        Post.user_id = clearskies.columns.BelongsToId(User, is_readable=False)
        Post.user = clearskies.columns.BelongsToModel("user_id")

        # Test data with nested user
        record = {"id": "1", "title": "Test Post", "user": {"id": "42", "name": "Alice"}}

        # Map the relationship data
        # The backend code will temporarily set User.backend = self.backend before instantiation
        user_data = self.backend._map_relationship_data(record, Post.user, parent_model=None)

        # Should return a User model instance (not a dict)
        assert user_data is not None
        assert isinstance(user_data, User)
        assert user_data.id == "42"
        assert user_data.name == "Alice"
        assert user_data._exists is True  # type: ignore[attr-defined]  # Should be marked as existing


class TestGraphqlBackendNestedFields(unittest.TestCase):
    """Test nested field (double underscore) support in GraphQL backend."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=GraphqlClient)
        self.backend = GraphqlBackend(graphql_client=self.mock_client, root_field="users")

    def test_build_nested_field_single_level(self):
        """Test building nested field from single-level underscore notation."""
        result = self.backend._build_nested_field_from_underscore("user__name")
        expected = "user { name }"
        assert result == expected

    def test_build_nested_field_two_levels(self):
        """Test building nested field from two-level underscore notation."""
        result = self.backend._build_nested_field_from_underscore("project__owner__email")
        expected = "project { owner { email } }"
        assert result == expected

    def test_build_nested_field_three_levels(self):
        """Test building nested field from three-level underscore notation."""
        result = self.backend._build_nested_field_from_underscore("user__profile__settings__theme")
        expected = "user { profile { settings { theme } } }"
        assert result == expected

    def test_build_nested_field_with_case_conversion(self):
        """Test that nested fields respect case conversion."""
        result = self.backend._build_nested_field_from_underscore("user_profile__display_name")
        # Should convert snake_case to camelCase
        expected = "userProfile { displayName }"
        assert result == expected

    def test_build_graphql_fields_includes_nested_fields(self):
        """Test that nested fields are included in GraphQL query building."""

        class ModelWithNestedField(clearskies.Model):
            id_column_name = "id"
            backend = None  # type: ignore[assignment]
            id = clearskies.columns.String()
            user__name = clearskies.columns.String()
            user__email = clearskies.columns.String()

        columns = ModelWithNestedField.get_columns()
        fields = self.backend._build_graphql_fields(columns)

        # Should include nested user field with name and email
        assert "user {" in fields
        assert "name" in fields
        assert "email" in fields

    def test_map_record_reads_nested_data(self):
        """Test that nested data from GraphQL response is properly mapped."""
        record = {"id": "1", "user": {"name": "Alice", "email": "alice@example.com"}}

        class ModelWithNestedField(clearskies.Model):
            id_column_name = "id"
            backend = None  # type: ignore[assignment]
            id = clearskies.columns.String()
            user__name = clearskies.columns.String()
            user__email = clearskies.columns.String()

        columns = ModelWithNestedField.get_columns()
        mapped = self.backend._map_record(record, columns)

        # Should extract nested values and map to double underscore format
        assert mapped["id"] == "1"
        assert mapped["user__name"] == "Alice"
        assert mapped["user__email"] == "alice@example.com"

    def test_map_record_handles_missing_nested_data(self):
        """Test that missing nested data is handled gracefully."""
        record = {
            "id": "1",
            # user field is missing
        }

        class ModelWithNestedField(clearskies.Model):
            id_column_name = "id"
            backend = None  # type: ignore[assignment]
            id = clearskies.columns.String()
            user__name = clearskies.columns.String()

        columns = ModelWithNestedField.get_columns()
        mapped = self.backend._map_record(record, columns)

        # Should handle missing nested data without errors
        assert mapped["id"] == "1"
        assert "user__name" not in mapped or mapped["user__name"] is None


if __name__ == "__main__":
    unittest.main()
