from typing import TYPE_CHECKING, Any

from clearskies.cursors.base_cursor import CursorProxy
from clearskies.cursors.sqlite_cursor import SqliteCursor
from clearskies.di import AdditionalConfig

if TYPE_CHECKING:
    from clearskies import Environment


class SqliteConfig(AdditionalConfig):
    """Configuration for SQLite cursor backend."""

    def provide_cursor_backend_type(self) -> str:
        """Return the type of cursor backend this config is for."""
        return "sqlite"

    def provide_cursor(self, connection_details: dict[str, Any]) -> "CursorProxy":
        """Provide a SQLite cursor proxy with autocommit enabled."""
        cursor_config = SqliteCursor(
            database_name=connection_details["database_name"],
            autocommit=True,
        )
        # Return the actual cursor proxy, not the config
        return cursor_config()

    def provide_connection_details(self, environment: "Environment") -> dict[str, Any]:
        """Provide the connection details for the SQLite database."""
        return {
            "database_name": environment.get("DATABASE_NAME") if environment.get("DATABASE_NAME", True) else ":memory:",
        }
