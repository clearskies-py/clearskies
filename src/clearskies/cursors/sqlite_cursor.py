from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING, Any

from clearskies.configs import string
from clearskies.cursors import base_cursor
from clearskies.di import inject

if TYPE_CHECKING:
    from sqlite3 import Connection


class SqliteCursor(base_cursor.BaseCursor):
    """Configuration for SQLite cursor backend."""

    cursor_type: str = "sqlite"

    parameter_style = string.String(required=False, default="qmark")

    sys = inject.ByName("sys")

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor."""
        try:
            return object.__getattribute__(self, "_factory")
        except AttributeError:
            try:
                import sqlite3

                object.__setattr__(self, "_factory", sqlite3)
                return sqlite3
            except ImportError as e:
                raise ValueError(  # noqa: TRY003
                    "The cursor requires sqlite3 to be available. sqlite3 is included with the standard library for Python, "
                    f"so this error likely indicates a misconfigured Python installation. Error: {e}"
                ) from e

    @property
    def connection(self) -> Connection:
        """Provide a SQLite connection with autocommit disabled."""
        import sys

        def dict_factory(cursor, row):
            fields = [column[0] for column in cursor.description]
            return dict(zip(fields, row))

        connection = self.factory.connect(
            database=self.database_name,
            timeout=2.0,
        )
        connection.row_factory = dict_factory
        if not self.autocommit:
            """Sqlite autocommit is enabled by default, so only set isolation_level to None
            when autocommit is disabled."""
            if sys.version_info > (3, 12):  # noqa: UP036
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
