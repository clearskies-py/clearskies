from typing import TYPE_CHECKING, Any

from clearskies.di import AdditionalConfig

if TYPE_CHECKING:
    from psycopg import Connection, Cursor

    from clearskies import Environment


class PostgresqlConfig(AdditionalConfig):
    """Configuration for PostgreSQL cursor backend."""

    def provide_cursor_backend_type(self) -> str:
        """Return the type of cursor backend this config is for."""
        return "postgresql"

    def provide_connection_no_autocommit(self, connection_details: dict[str, Any]) -> "Connection":
        """Provide a PostgreSQL connection with autocommit disabled."""
        try:
            import psycopg
            from psycopg.rows import dict_row
        except:
            raise ValueError(
                "The cursor requires psycopg to be installed.  This is an optional dependency of clearskies, so to include it do a `pip install 'clear-skies[pgsql]'`"
            )
        return psycopg.connect(
            user=connection_details["username"],
            password=connection_details["password"],
            host=connection_details["host"],
            database=connection_details["database"],
            port=connection_details.get("port", 5432),
            sslcert=connection_details.get("sslcert", None),
            connect_timeout=2,
            autocommit=False,
            row_factory=dict_row,
        )

    def provide_connection(self, connection_details: dict[str, Any]) -> "Connection":
        """Provide a PostgreSQL connection with autocommit enabled."""
        try:
            import psycopg
            from psycopg.rows import dict_row
        except:
            raise ValueError(
                "The cursor requires psycopg to be installed.  This is an optional dependency of clearskies, so to include it do a `pip install 'clear-skies[pgsql]'`"
            )

        return psycopg.connect(
            user=connection_details["username"],
            password=connection_details["password"],
            host=connection_details["host"],
            database=connection_details["database"],
            port=connection_details.get("port", 5432),
            ssl_ca=connection_details.get("ssl_ca", None),
            autocommit=True,
            connect_timeout=2,
            row_factory=dict_row,
        )

    def provide_connection_details(self, environment: "Environment") -> dict[str, Any]:
        """Provide the connection details for the PostgreSQL database."""
        try:
            port = environment.get("db_port")
        except:
            port = 5432

        try:
            sslcert = environment.get("db_sslcert")
        except:
            sslcert = None

        return {
            "username": environment.get("db_username"),
            "password": environment.get("db_password"),
            "host": environment.get("db_host"),
            "database": environment.get("db_database"),
            "port": port,
            "sslcert": sslcert,
        }

    def provide_cursor(self, connection: "Connection") -> "Cursor":
        """Provide a PostgreSQL cursor from the given connection."""
        with connection.cursor() as cursor:
            return cursor
