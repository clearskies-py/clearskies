"""Tests for GraphQL client."""

import unittest
from unittest.mock import Mock, patch

from clearskies.clients import GraphqlClient


class TestGraphqlClient(unittest.TestCase):
    """Test GraphQL client functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.endpoint = "https://api.example.com/graphql"
        self.client = GraphqlClient(endpoint=self.endpoint)

    def test_initialization_with_endpoint(self):
        """Test client can be initialized with an endpoint."""
        assert self.client.endpoint == self.endpoint

    def test_initialization_with_authentication(self):
        """Test client can be initialized with authentication."""
        mock_auth = Mock()
        client = GraphqlClient(endpoint=self.endpoint, authentication=mock_auth)
        assert client.authentication == mock_auth

    def test_initialization_with_timeout(self):
        """Test client can be initialized with custom timeout."""
        client = GraphqlClient(endpoint=self.endpoint, timeout=60)
        assert client.timeout == 60

    @patch("gql.Client")
    def test_client_property_creates_gql_client(self, mock_gql_client):
        """Test that accessing client property creates gql Client."""
        # Access the client property
        _ = self.client.client

        # Verify gql Client was created
        mock_gql_client.assert_called_once()

    @patch("gql.Client")
    def test_execute_builds_and_executes_query(self, mock_gql_client):
        """Test that execute method builds and runs a GraphQL query."""
        # Setup
        mock_client_instance = Mock()
        mock_gql_client.return_value = mock_client_instance
        mock_client_instance.execute.return_value = {"data": {"users": []}}

        query = "query { users { id name } }"

        # Execute
        result = self.client.execute(query)

        # Verify
        assert result == {"data": {"users": []}}
        mock_client_instance.execute.assert_called_once()

    @patch("gql.Client")
    def test_execute_with_variables(self, mock_gql_client):
        """Test execute with query variables."""
        mock_client_instance = Mock()
        mock_gql_client.return_value = mock_client_instance
        mock_client_instance.execute.return_value = {"data": {"user": {"id": "1"}}}

        query = "query($id: ID!) { user(id: $id) { id name } }"
        variables = {"id": "1"}

        result = self.client.execute(query, variable_values=variables)

        assert result == {"data": {"user": {"id": "1"}}}

    def test_authentication_integration(self):
        """Test that authentication is properly integrated."""
        mock_auth = Mock()
        mock_auth.get_headers.return_value = {"Authorization": "Bearer token123"}

        client = GraphqlClient(endpoint=self.endpoint, authentication=mock_auth)

        assert client.authentication == mock_auth


if __name__ == "__main__":
    unittest.main()
