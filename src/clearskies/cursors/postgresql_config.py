from typing import TYPE_CHECKING, Any

from clearskies.cursors.base_cursor import CursorProxy
from clearskies.di import AdditionalConfig

if TYPE_CHECKING:
    from clearskies import Environment


class PostgresqlConfig(AdditionalConfig):
    """Configuration for PostgreSQL cursor backend."""

    def provide_cursor_backend_type(self) -> str:
        """Return the type of cursor backend this config is for."""
        return "postgresql"

    def provide_cursor(self, connection_details: dict[str, Any]) -> "CursorProxy":
        """Provide a PostgreSQL connection with autocommit disabled."""
        from clearskies.cursors.postgresql_cursor import PostgresqlCursor

        cursor = PostgresqlCursor(
            username=connection_details["database_username"],
            password=connection_details["database_password"],
            host=connection_details["database_host"],
            database_name=connection_details["database_name"],
            port=connection_details.get("database_port", 5432),
            sslcert=connection_details.get("database_sslcert", None),
            autocommit=False,
        )
        return cursor()

    def provide_connection_details(self, environment: "Environment") -> dict[str, Any]:
        """Provide the connection details for the PostgreSQL database."""
        try:
            username = environment.get("database_username")
        except:
            username = "root"

        try:
            password = environment.get("database_password")
        except:
            password = ""

        try:
            host = environment.get("database_host")
        except:
            host = "localhost"

        try:
            port = environment.get("database_port")
        except:
            port = 5432

        try:
            sslcert = environment.get("database_sslcert")
        except:
            sslcert = ""

        return {
            "database_username": username,
            "database_password": password,
            "database_host": host,
            "database_name": environment.get("database_name"),
            "database_port": port,
            "database_sslcert": sslcert,
        }
