import unittest
from types import SimpleNamespace

import clearskies.cursors
from clearskies.di import Di


class PostgresqlConfigTest(unittest.TestCase):
    """Tests for the PostgresqlConfig AdditionalConfig class."""

    def get_environment(self, key):
        if key == "database_name":
            return "test"
        raise KeyError("Oops")

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
        assert isinstance(cursor_instance, clearskies.cursors.Postgresql)

    def test_cursor_override_by_backend_type(self):
        def my_function(cursor):
            return cursor

        di = Di(
            bindings={"cursor_backend_type": "postgresql", "environment": SimpleNamespace(get=self.get_environment)},
        )

        cursor_instance = di.call_function(my_function)
        assert isinstance(cursor_instance, clearskies.cursors.Postgresql)

    def test_cursor_override_by_name(self):
        def my_function(cursor):
            return cursor

        di = Di(
            bindings={"cursor": clearskies.cursors.Postgresql(database_name="test")},
        )

        cursor_instance = di.call_function(my_function)
        assert isinstance(cursor_instance, clearskies.cursors.Postgresql)
