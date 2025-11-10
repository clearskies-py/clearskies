from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pymysql.connections import Connection
    from pymysql.cursors import Cursor

    from clearskies import Environment

from clearskies.di import AdditionalConfig


class MysqlConfig(AdditionalConfig):
    """Configuration for MySQL cursor backend."""

    def provide_cursor_backend_type(self):
        """Return the type of cursor backend this config is for."""
        return "mysql"  # must match the name used in the connection URL, e.g. mysql://user:pass@host/db

    def provide_connection_no_autocommit(self, connection_details: dict[str, Any]) -> "Connection[Cursor]":
        """Provide a MySQL connection with autocommit disabled."""
        from clearskies.cursors.mysql_cursor import MysqlCursor

        cursor = MysqlCursor(
            username=connection_details["database_username"],
            password=connection_details["database_password"],
            host=connection_details["database_host"],
            database_name=connection_details["database_name"],
            port=connection_details.get("database_port", 5432),
            ssl_ca=connection_details.get("ssl_ca", None),
            autocommit=False,
        )
        return cursor.connection

    def provide_connection(self, connection_details: dict[str, Any]) -> "Connection[Cursor]":
        """Provide a MySQL connection with autocommit enabled."""
        from clearskies.cursors.mysql_cursor import MysqlCursor

        cursor = MysqlCursor(
            username=connection_details["database_username"],
            password=connection_details["database_password"],
            host=connection_details["database_host"],
            database_name=connection_details["database_name"],
            port=connection_details.get("database_port", 5432),
            ssl_ca=connection_details.get("ssl_ca", None),
            autocommit=True,
        )
        return cursor.connection

    def provide_connection_details(self, environment: "Environment") -> dict[str, Any]:
        """Provide the connection details for the MySQL database."""
        try:
            port = environment.get("db_port")
        except:
            port = 3306

        try:
            ssl_ca = environment.get("db_ssl_ca")
        except:
            ssl_ca = None

        return {
            "username": environment.get("db_username"),
            "password": environment.get("db_password"),
            "host": environment.get("db_host"),
            "database": environment.get("db_database"),
            "port": port,
            "ssl_ca": ssl_ca,
        }

    def provide_cursor(self, connection: "Connection") -> "Cursor":
        """Provide a MySQL cursor from the given connection."""
        return connection.cursor()
