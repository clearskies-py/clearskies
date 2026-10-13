import unittest
from unittest.mock import MagicMock, call

import clearskies
from clearskies.contexts import Context


class CursorBackendTest(unittest.TestCase):
    def test_overview(self):
        class UserPreference(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.CursorBackend(table_prefix="configuration_")
            id = clearskies.columns.Uuid()

            @classmethod
            def destination_name(cls):
                return "preferences"

        cursor = MagicMock()
        cursor.execute = MagicMock()
        cursor.execute.side_effect = [None, None]
        cursor.__iter__ = lambda self: [{"id": "1-2-3-4"}].__iter__()
        cursor.value_placeholder = "%s"
        cursor.table_escape_character = "`"
        cursor.column_escape_character = "`"

        uuid = MagicMock()
        uuid.uuid4 = MagicMock(return_value=["1-2-3-4"])

        context = Context(
            clearskies.endpoints.Callable(
                lambda user_preferences: user_preferences.create(no_data=True).id,
            ),
            classes=[UserPreference],
            bindings={
                "global_table_prefix": "user_",
                "cursor": cursor,
                "uuid": uuid,
            },
        )

        status_code, response, response_headers = context()
        assert status_code == 200
        assert response["data"] == "1-2-3-4"
        cursor.execute.assert_has_calls(
            [
                call("INSERT INTO `user_configuration_preferences` (`id`) VALUES (%s)", ("['1-2-3-4']",)),
                call(
                    "SELECT `user_configuration_preferences`.* FROM `user_configuration_preferences` WHERE user_configuration_preferences.id=%s",
                    ("['1-2-3-4']",),
                ),
            ]
        )

    def test_raw_dbapi_cursor_raises_type_error(self):
        import sqlite3

        class UserPreference(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.CursorBackend()
            id = clearskies.columns.Uuid()

        context = Context(
            clearskies.endpoints.Callable(
                lambda user_preferences: user_preferences.create(no_data=True).id,
            ),
            classes=[UserPreference],
            bindings={"cursor": sqlite3.connect(":memory:").cursor()},
        )

        with self.assertRaisesRegex(TypeError, r"clearskies\.cursors\.Sqlite"):
            context()

    def test_cursor_from_additional_config(self):
        class UserPreference(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.CursorBackend()
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        class DatabaseConfig(clearskies.di.AdditionalConfig):
            def provide_cursor(self, secrets):
                cursor = clearskies.cursors.Sqlite(database=secrets.get("/path/to/database"))
                cursor.execute("CREATE TABLE user_preferences (id TEXT PRIMARY KEY, name TEXT)")
                return cursor

        secrets = MagicMock()
        secrets.get = MagicMock(return_value=":memory:")

        context = Context(
            clearskies.endpoints.Callable(
                lambda user_preferences: user_preferences.create({"name": "alice"}).name,
            ),
            classes=[UserPreference],
            additional_configs=[DatabaseConfig()],
            bindings={"secrets": secrets},
        )

        status_code, response, _ = context()
        assert status_code == 200
        assert response["data"] == "alice"
