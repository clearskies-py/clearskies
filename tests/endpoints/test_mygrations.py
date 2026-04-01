import unittest
from unittest.mock import MagicMock, patch

import clearskies


class MygrationsTest(unittest.TestCase):
    # A. Cursor dual-path resolution

    def test_cursor_resolved_from_di_by_default(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["mygrations 1.0"], True]):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version"),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        assert status_code == 200
        assert response_data["status"] == "success"

    def test_direct_cursor_takes_precedence_over_di(self):
        di_cursor = MagicMock()
        di_cursor.autocommit = True
        di_cursor.connection = MagicMock()

        explicit_cursor = MagicMock()
        explicit_cursor.autocommit = False
        explicit_cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["mygrations 1.0"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version", cursor=explicit_cursor),
                bindings={"cursor": di_cursor},
            )
            status_code, response_data, response_headers = context()

        call_kwargs = mock_execute.call_args[0][1]
        assert call_kwargs["connection"] is explicit_cursor.connection

    def test_custom_cursor_dependency_name(self):
        custom_cursor = MagicMock()
        custom_cursor.autocommit = True
        custom_cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["mygrations 1.0"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version", cursor_dependency_name="my_custom_cursor"),
                bindings={"my_custom_cursor": custom_cursor},
            )
            status_code, response_data, response_headers = context()

        assert status_code == 200
        call_kwargs = mock_execute.call_args[0][1]
        assert call_kwargs["connection"] is custom_cursor.connection

    # B. handle() happy paths

    def test_version_command(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["mygrations 1.0.0"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version"),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        assert status_code == 200
        assert response_data["status"] == "success"
        assert response_data["data"] == ["mygrations 1.0.0"]
        mock_execute.assert_called_once_with(
            "version",
            {"connection": cursor.connection, "sql_files": ["./database"]},
            print_results=False,
        )

    def test_plan_command(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["ALTER TABLE ..."], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="plan"),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        assert status_code == 200
        assert response_data["status"] == "success"
        assert response_data["data"] == ["ALTER TABLE ..."]
        mock_execute.assert_called_once_with(
            "plan",
            {"connection": cursor.connection, "sql_files": ["./database"]},
            print_results=False,
        )

    def test_apply_command(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["Applied 3 changes"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="apply"),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        assert status_code == 200
        mock_execute.assert_called_once()
        assert mock_execute.call_args[0][0] == "apply"

    # C. handle() failure paths

    def test_execute_failure_returns_client_error(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["Table error", "Column mismatch"], False]):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="plan"),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        assert status_code == 400
        assert response_data["status"] == "client_error"
        assert "Table error" in response_data["error"]
        assert "Column mismatch" in response_data["error"]

    def test_mygrations_not_installed_raises_value_error(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch.dict("sys.modules", {"mygrations": None, "mygrations.core": None, "mygrations.core.commands": None}):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version"),
                bindings={"cursor": cursor},
            )
            with self.assertRaises((ValueError, ModuleNotFoundError)):
                context()

    # D. Command validation with allow_input

    def test_invalid_command_with_allow_input_returns_input_errors(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[[], True]):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(allow_input=True),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context(body={"command": "invalid_command"})

        assert status_code == 200
        assert response_data["status"] == "input_errors"
        assert "command" in response_data["input_errors"]
        assert "invalid_command" in response_data["input_errors"]["command"]

    # E. allow_input flag behavior

    def test_allow_input_false_ignores_body(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["plan output"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="plan", allow_input=False),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context(body={"command": "apply"})

        assert status_code == 200
        assert mock_execute.call_args[0][0] == "plan"

    def test_allow_input_true_reads_command_from_body(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["apply output"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version", allow_input=True),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context(body={"command": "apply"})

        assert status_code == 200
        assert mock_execute.call_args[0][0] == "apply"

    def test_allow_input_true_falls_back_to_config_when_body_empty(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["version output"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version", allow_input=True),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context(body={})

        assert status_code == 200
        assert mock_execute.call_args[0][0] == "version"

    # F. Autocommit save/restore

    def test_autocommit_disabled_during_execution(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        autocommit_calls = []
        cursor.set_autocommit.side_effect = lambda v: autocommit_calls.append(v)

        with patch("mygrations.core.commands.execute", return_value=[["ok"], True]):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version"),
                bindings={"cursor": cursor},
            )
            context()

        assert autocommit_calls == [False, True]

    def test_autocommit_restored_on_execute_exception(self):
        cursor = MagicMock()
        cursor.autocommit = False
        cursor.connection = MagicMock()

        autocommit_calls = []
        cursor.set_autocommit.side_effect = lambda v: autocommit_calls.append(v)

        with patch("mygrations.core.commands.execute", side_effect=RuntimeError("boom")):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version"),
                bindings={"cursor": cursor},
            )
            with self.assertRaises(RuntimeError):
                context()

        assert autocommit_calls == [False, False]

    # G. Module migrations merge

    def test_include_module_migrations_false_uses_only_sql(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["ok"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(
                    command="version",
                    sql=["./my_sql/"],
                    include_module_migrations=False,
                ),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        assert status_code == 200
        call_kwargs = mock_execute.call_args[0][1]
        assert call_kwargs["sql_files"] == ["./my_sql/"]

    def test_include_module_migrations_true_prepends_auto_paths(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with (
            patch("mygrations.core.commands.execute", return_value=[["ok"], True]) as mock_execute,
            patch.object(
                clearskies.di.Di,
                "get_mygrations_sql_paths",
                return_value=["./module_a/", "./module_b/"],
            ),
        ):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(
                    command="version",
                    sql=["./my_sql/"],
                    include_module_migrations=True,
                ),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        assert status_code == 200
        call_kwargs = mock_execute.call_args[0][1]
        assert call_kwargs["sql_files"] == ["./module_a/", "./module_b/", "./my_sql/"]

    def test_module_migrations_deduplication(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with (
            patch("mygrations.core.commands.execute", return_value=[["ok"], True]) as mock_execute,
            patch.object(
                clearskies.di.Di,
                "get_mygrations_sql_paths",
                return_value=["./my_sql/", "./unique_module/"],
            ),
        ):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(
                    command="version",
                    sql=["./my_sql/"],
                    include_module_migrations=True,
                ),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        call_kwargs = mock_execute.call_args[0][1]
        assert call_kwargs["sql_files"] == ["./unique_module/", "./my_sql/"]

    def test_module_migrations_allowlist_filters_classes(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with (
            patch("mygrations.core.commands.execute", return_value=[["ok"], True]) as mock_execute,
            patch.object(
                clearskies.di.Di,
                "get_mygrations_sql_paths",
                return_value=["./filtered_path/"],
            ) as mock_get_paths,
        ):
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(
                    command="version",
                    sql=["./my_sql/"],
                    include_module_migrations=True,
                    module_migrations=["SpecificMigration"],
                ),
                bindings={"cursor": cursor},
            )
            status_code, response_data, response_headers = context()

        mock_get_paths.assert_called_once_with(["SpecificMigration"])

    # H. SQL configuration

    def test_default_sql_path(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["ok"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version"),
                bindings={"cursor": cursor},
            )
            context()

        call_kwargs = mock_execute.call_args[0][1]
        assert call_kwargs["sql_files"] == ["./database"]

    def test_custom_sql_paths(self):
        cursor = MagicMock()
        cursor.autocommit = True
        cursor.connection = MagicMock()

        with patch("mygrations.core.commands.execute", return_value=[["ok"], True]) as mock_execute:
            context = clearskies.contexts.Context(
                clearskies.endpoints.Mygrations(command="version", sql=["./schema/", "./extra.sql"]),
                bindings={"cursor": cursor},
            )
            context()

        call_kwargs = mock_execute.call_args[0][1]
        assert call_kwargs["sql_files"] == ["./schema/", "./extra.sql"]
