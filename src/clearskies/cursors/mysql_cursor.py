from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pymysql.connections import Connection


from clearskies.configs import integer, string
from clearskies.cursors import base_cursor
from clearskies.decorators import parameters_to_properties


class MysqlCursor(base_cursor.BaseCursor):
    """Configuration for MySQL cursor backend."""

    cursor_type: str = "mysql"

    host = string.String(default="localhost")
    port = integer.Integer(default=3306)
    database_name = string.String(default="mysql")
    username = string.String(default="root")
    password = string.String(default=None)
    cert_path = string.String(default=None)

    @parameters_to_properties
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        autocommit: bool | None = None,
        cert_path: str | None = None,
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

        if environment.get("DATABASE_HOST", True):
            self.host = environment.get("DATABASE_HOST")
        if environment.get("DATABASE_PORT", True):
            self.port = environment.get("DATABASE_PORT")
        if environment.get("DATABASE_USERNAME", True):
            self.username = environment.get("DATABASE_USERNAME")
        if environment.get("DATABASE_PASSWORD", True):
            self.password = environment.get("DATABASE_PASSWORD")
        if environment.get("DATABASE_AUTOCOMMIT", True):
            self.autocommit = environment.get("DATABASE_AUTOCOMMIT")
        if environment.get("DATABASE_CERT_PATH", True):
            self.cert_path = environment.get("DATABASE_CERT_PATH")

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor."""
        try:
            return object.__getattribute__(self, "_factory")
        except AttributeError:
            try:
                import pymysql

                object.__setattr__(self, "_factory", pymysql)
                return pymysql
            except:
                raise ValueError(
                    "The cursor requires pymysql to be installed.  This is an optional dependency of clearskies, so to include it do a `pip install 'clear-skies[mysql]'`"
                )

    @property
    def connection(self) -> "Connection":
        """Return the connection for the cursor."""
        self.configure()
        return self.factory.connect(
            user=self.username,
            password=self.password,
            host=self.host,
            database=self.database_name,
            port=self.port,
            cursorclass=self.factory.cursors.DictCursor,
            autocommit=self.autocommit,
            ssl_ca=self.cert_path if self.cert_path else None,
        )

    def provide_connection_details(self) -> dict[str, Any]:
        """Provide the connection details for the MySQL database."""
        return {
            "username": self.username,
            "password": self.password,
            "host": self.host,
            "database": self.database_name,
            "port": self.port,
            "cert_path": self.cert_path,
            "autocommit": self.autocommit,
        }
