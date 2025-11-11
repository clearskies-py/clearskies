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
            username=connection_details["username"],
            password=connection_details["password"],
            host=connection_details["host"],
            database_name=connection_details["database"],
            port=connection_details.get("port", 5432),
            cert_path=connection_details.get("cert_path", None),
            autocommit=False,
        )
        return cursor()

    def provide_connection_details(self, environment: "Environment") -> dict[str, Any]:
        """Provide the connection details for the PostgreSQL database."""
        try:
            username = environment.get("DATABASE_USERNAME")
        except:
            username = "postgres"

        try:
            password = environment.get("DATABASE_PASSWORD")
        except:
            password = ""

        try:
            host = environment.get("DATABASE_HOST")
        except:
            host = "localhost"

        try:
            port = environment.get("DATABASE_PORT")
        except:
            port = 5432

        try:
            cert_path = environment.get("DATABASE_CERT_PATH")
        except:
            cert_path = ""

        return {
            "username": username,
            "password": password,
            "host": host,
            "database": environment.get("DATABASE_NAME"),
            "port": port,
            "cert_path": cert_path,
        }
