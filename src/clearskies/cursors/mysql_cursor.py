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
    ssl_ca = string.String(default=None)

    @parameters_to_properties
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        autocommit: bool | None = None,
        ssl_ca: str | None = None,
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
        if environment.get("database_ssl_ca", True):
            self.ssl_ca = environment.get("database_ssl_ca")

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
            ssl_ca=self.ssl_ca if self.ssl_ca else None,
        )

    def provide_connection_details(self) -> dict[str, Any]:
        """Provide the connection details for the MySQL database."""
        return {
            "username": self.username,
            "password": self.password,
            "host": self.host,
            "database": self.database_name,
            "port": self.port,
            "ssl_ca": self.ssl_ca,
            "autocommit": self.autocommit,
        }
