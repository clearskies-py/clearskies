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
    ):
        self.configure()

    def configure(self) -> None:
        """Configure the cursor."""
        super().configure()
        if self.environment.get("database_host", True):
            self.host = self.environment.get("database_host")
        if self.environment.get("database_port", True):
            self.port = self.environment.get("database_port")
        if self.environment.get("database_username", True):
            self.username = self.environment.get("database_username")
        if self.environment.get("database_password", True):
            self.password = self.environment.get("database_password")
        if self.environment.get("database_autocommit", True):
            self.autocommit = self.environment.get("database_autocommit")
        if self.environment.get("database_sslcert", True):
            self.sslcert = self.environment.get("database_sslcert")

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor."""
        if not hasattr(self, "_factory"):
            try:
                import psycopg

                self._factory = psycopg
            except ImportError:
                raise ValueError(
                    "The cursor requires psycopg to be installed.  This is an optional dependency of clearskies, so to include it do a `pip install 'clear-skies[pgsql]'`"
                )
        return self._factory

    @property
    def connection(self) -> "Connection":
        """Return the connection for the cursor."""
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
