import unittest
from types import SimpleNamespace

import pytest

import clearskies.cursors
from clearskies.di import Di


class PostgresqlConfigTest(unittest.TestCase):
    """Tests for the PostgresqlConfig AdditionalConfig class."""

    def get_environment(self, key):
        print(f"Getting environment key: {key}")
        if key == "database_password":
            print(f"Found database_password: secret")
            return "secret"
        if key == "database_name":
            print(f"Found database_name: test")
            return "test"
        raise KeyError("Oops")

    @pytest.mark.broken
    def test_cursor_override_by_config(self):
        def my_function(cursor):
            return cursor

        di = Di(
            additional_configs=[clearskies.cursors.PostgresqlConfig()],
            bindings={
                "environment": SimpleNamespace(get=self.get_environment),
            },
        )
        cursor_instance = di.call_function(my_function)
        assert isinstance(cursor_instance, clearskies.cursors.PostgresqlCursor)

    def test_cursor_override_by_backend_type(self):
        def my_function(cursor):
            return cursor

        di = Di(
            bindings={"cursor_backend_type": "postgresql", "environment": SimpleNamespace(get=self.get_environment)},
        )

        cursor_instance = di.call_function(my_function)
        assert isinstance(cursor_instance.database_name, clearskies.cursors.PostgresqlCursor)

    @pytest.mark.broken
    def test_cursor_override_by_name(self):
        def my_function(cursor):
            return cursor

        di = Di(
            bindings={"cursor": clearskies.cursors.PostgresqlCursor(database_name="test")},
        )

        cursor_instance = di.call_function(my_function)
        assert isinstance(cursor_instance, clearskies.cursors.PostgresqlCursor)
