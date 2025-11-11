from types import ModuleType
from typing import TYPE_CHECKING

from clearskies.configs import boolean, integer, string
from clearskies.cursors import base_cursor
from clearskies.decorators import parameters_to_properties

if TYPE_CHECKING:
    from psycopg import Connection


class PostgresqlCursor(base_cursor.BaseCursor):
    """Configuration for PostgreSQL cursor backend."""

    cursor_type: str = "postgresql"

    host = string.String(default="localhost")
    port = integer.Integer(default=5432)
    database_name = string.String(default=None)
    username = string.String(default="postgres")
    password = string.String(default="")
    autocommit = boolean.Boolean(default=True)
    sslcert = string.String(default=None)

    @parameters_to_properties
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        sslcert: str | None = None,
        autocommit: bool | None = None,
        parameter_style: str | None = None,
    ):
        self.finalize_and_validate_configuration()

    def configure(self) -> None:
        """Configure the cursor."""
        super().configure()

        # Check if environment has been injected
        try:
            environment = object.__getattribute__(self, "environment")
        except AttributeError:
            # Environment not injected, skip configuration from environment
            return

        if environment.get("database_host", True):
            self.host = environment.get("database_host")
        if environment.get("database_port", True):
            self.port = environment.get("database_port")
        if environment.get("database_username", True):
            self.username = environment.get("database_username")
        if environment.get("database_password", True):
            self.password = environment.get("database_password")
        if environment.get("database_autocommit", True):
            self.autocommit = environment.get("database_autocommit")
        if environment.get("database_sslcert", True):
            self.sslcert = environment.get("database_sslcert")

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor."""
        try:
            return object.__getattribute__(self, "_factory")
        except AttributeError:
            try:
                import psycopg

                object.__setattr__(self, "_factory", psycopg)
                return psycopg
            except ImportError:
                raise ValueError(
                    "The cursor requires psycopg to be installed.  This is an optional dependency of clearskies, so to include it do a `pip install 'clear-skies[pgsql]'`"
                )

    @property
    def connection(self) -> "Connection":
        """Return the connection for the cursor."""
        self.configure()
        return self.factory.connect(
            user=self.username,
            password=self.password,
            host=self.host,
            dbname=self.database_name,
            port=self.port,
            connect_timeout=2,
            autocommit=self.autocommit,
            sslcert=self.sslcert,
            row_factory=self.factory.rows.dict_row,
        )
