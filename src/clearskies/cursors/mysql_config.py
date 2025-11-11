from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pymysql.connections import Connection
    from pymysql.cursors import Cursor

    from clearskies.cursors.base_cursor import CursorProxy


from clearskies.di import AdditionalConfig


class MysqlConfig(AdditionalConfig):
    """Configuration for MySQL cursor backend."""

    def provide_cursor_backend_type(self):
        """Return the type of cursor backend this config is for."""
        return "mysql"  # must match the name used in the connection URL, e.g. mysql://user:pass@host/db

    def provide_cursor(self, connection_details: dict[str, Any]) -> "CursorProxy":
        """Provide a MySQL connection with autocommit disabled."""
        from clearskies.cursors.mysql_cursor import MysqlCursor

        cursor = MysqlCursor(
            username=connection_details["username"],
            password=connection_details["password"],
            host=connection_details["host"],
            database_name=connection_details["database"],
            port=connection_details.get("port", 3306),
            cert_path=connection_details.get("cert_path", None),
            autocommit=False,
        )
        return cursor()

    def provide_connection(self, connection_details: dict[str, Any]) -> "Connection[Cursor]":
        """Provide a MySQL connection with autocommit enabled."""
        from clearskies.cursors.mysql_cursor import MysqlCursor

        cursor = MysqlCursor(
            username=connection_details["username"],
            password=connection_details["password"],
            host=connection_details["host"],
            database_name=connection_details["database"],
            port=connection_details.get("port", 3306),
            cert_path=connection_details.get("cert_path", None),
            autocommit=True,
        )
        return cursor.connection
