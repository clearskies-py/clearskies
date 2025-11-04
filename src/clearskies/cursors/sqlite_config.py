from typing import TYPE_CHECKING, Any

from clearskies.di import AdditionalConfig

if TYPE_CHECKING:
    from sqlite3 import Connection, Cursor

    from clearskies import Environment


class SqliteConfig(AdditionalConfig):
    """Configuration for SQLite cursor backend."""

    def provide_cursor_backend_type(self) -> str:
        """Return the type of cursor backend this config is for."""
        return "sqlite"

    def provide_connection_no_autocommit(self, connection_details: dict[str, Any]) -> "Connection":
        """Provide a SQLite connection with autocommit disabled."""
        import sqlite3
        import sys

        def dict_factory(cursor, row):
            fields = [column[0] for column in cursor.description]
            return {key: value for key, value in zip(fields, row)}

        connection = sqlite3.connect(
            database=str(connection_details["database"]),
            timeout=2.0,
        )
        connection.row_factory = dict_factory
        if sys.version_info > (3, 12):
            connection.autocommit = False
        else:
            connection.isolation_level = None  # Disable autocommit

        return connection

    def provide_connection(self, connection_details: dict[str, Any]) -> "Connection":
        """Provide a SQLite connection with autocommit enabled."""
        import sqlite3
        import sys

        def dict_factory(cursor, row):
            fields = [column[0] for column in cursor.description]
            return {key: value for key, value in zip(fields, row)}

        connection = sqlite3.connect(
            database=str(connection_details["database"]),
            timeout=2.0,
        )
        connection.row_factory = dict_factory
        if sys.version_info >= (3, 12):
            connection.autocommit = True
        else:
            connection.isolation_level = None  # Disable autocommit

        return connection

    def provide_connection_details(self, environment: "Environment") -> dict[str, Any]:
        """Provide the connection details for the SQLite database."""
        return {
            "database": environment.get("db_database") if environment.get("db_database", True) else ":memory:",
        }

    def provide_cursor(self, connection: "Connection") -> "Cursor":
        """Provide a SQLite cursor from the given connection."""
        return connection.cursor()
