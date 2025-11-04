from typing import TYPE_CHECKING, Any

from clearskies.cursors import base

if TYPE_CHECKING:
    from sqlite3 import Connection


class Sqlite(base.Base):
    """Configuration for SQLite cursor backend."""

    cursor_type: str = "sqlite"

    @property
    def connection(self) -> "Connection":
        """Provide a SQLite connection with autocommit disabled."""
        import sqlite3
        import sys

        def dict_factory(cursor, row):
            fields = [column[0] for column in cursor.description]
            return {key: value for key, value in zip(fields, row)}

        connection = sqlite3.connect(
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
