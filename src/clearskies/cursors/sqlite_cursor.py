from types import ModuleType
from typing import TYPE_CHECKING, Any

from clearskies.cursors import base_cursor
from clearskies.di import inject

if TYPE_CHECKING:
    from sqlite3 import Connection


class SqliteCursor(base_cursor.BaseCursor):
    """Configuration for SQLite cursor backend."""

    cursor_type: str = "sqlite"

    sys = inject.ByName("sys")  # type: ignore

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor."""
        if not hasattr(self, "_factory"):
            try:
                import sqlite3

                self._factory = sqlite3
            except:
                raise ValueError(
                    "The cursor requires sqlite3 to be available.  sqlite3 is included with the standard library for Python, so this error likely indicates a misconfigured Python installation."
                )
        return self._factory

    @property
    def connection(self) -> "Connection":
        """Provide a SQLite connection with autocommit disabled."""
        import sys

        def dict_factory(cursor, row):
            fields = [column[0] for column in cursor.description]
            return {key: value for key, value in zip(fields, row)}

        connection = self.factory.connect(
            database=self.database_name,
            timeout=2.0,
        )
        connection.row_factory = dict_factory
        if not self.autocommit:
            """Sqlite autocommit is enabled by default, so only set isolation_level to None
            when autocommit is disabled."""
            if sys.version_info > (3, 12):
                connection.autocommit = False
            else:
                connection.isolation_level = None  # Disable autocommit

        return connection

    @property
    def connection_details(self) -> dict[str, Any]:
        """Provide the connection details for the SQLite database."""
        return {
            "database": self.database_name,
        }
