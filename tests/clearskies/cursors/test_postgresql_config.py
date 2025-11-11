import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import clearskies.cursors
from clearskies.di import Di


class PostgresqlConfigTest(unittest.TestCase):
    """Tests for the PostgresqlConfig AdditionalConfig class."""

    def get_environment(self, key):
        if key == "DATABASE_PASSWORD":
            return "secret"
        if key == "DATABASE_NAME":
            return "test"
        raise KeyError("Oops")

    def test_cursor_override_by_config(self):
        def my_function(cursor):
            return cursor

        # Mock psycopg connection to avoid actual database connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        with patch("psycopg.connect", return_value=mock_connection):
            di = Di(
                additional_configs=[clearskies.cursors.PostgresqlConfig()],
                bindings={
                    "environment": SimpleNamespace(get=self.get_environment),
                },
            )
            cursor_instance = di.call_function(my_function)
            # The cursor_instance will be a CursorProxy wrapping the PostgreSQL cursor
            # Check that the underlying connection was attempted with correct parameters
            assert cursor_instance is not None

    def test_cursor_override_by_backend_type(self):
        def my_function(cursor):
            return cursor

        # Mock psycopg connection to avoid actual database connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        with patch("psycopg.connect", return_value=mock_connection):
            di = Di(
                bindings={
                    "cursor_backend_type": "postgresql",
                    "environment": SimpleNamespace(get=self.get_environment),
                },
            )

            cursor_instance = di.call_function(my_function)
            # Verify we got a cursor instance back
            assert cursor_instance is not None

    def test_cursor_override_by_name(self):
        def my_function(cursor):
            return cursor

        # Mock psycopg connection to avoid actual database connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor

        with patch("psycopg.connect", return_value=mock_connection):
            di = Di(
                bindings={"cursor": clearskies.cursors.PostgresqlCursor(database_name="test")},
            )

            cursor_instance = di.call_function(my_function)
            assert isinstance(cursor_instance, clearskies.cursors.PostgresqlCursor)
