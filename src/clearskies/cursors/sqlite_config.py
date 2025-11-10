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
        from clearskies.cursors.sqlite_cursor import SqliteCursor

        cursor = SqliteCursor(
            database_name=connection_details["database_name"],
            autocommit=False,
        )
        return cursor.connection

    def provide_connection(self, connection_details: dict[str, Any]) -> "Connection":
        """Provide a SQLite connection with autocommit enabled."""
        from clearskies.cursors.sqlite_cursor import SqliteCursor

        cursor = SqliteCursor(
            database_name=connection_details["database_name"],
            autocommit=True,
        )
        return cursor.connection

    def provide_connection_details(self, environment: "Environment") -> dict[str, Any]:
        """Provide the connection details for the SQLite database."""
        return {
            "database": environment.get("database_name") if environment.get("database_name", True) else ":memory:",
        }

    def provide_cursor(self, connection: "Connection") -> "Cursor":
        """Provide a SQLite cursor from the given connection."""
        return connection.cursor()
