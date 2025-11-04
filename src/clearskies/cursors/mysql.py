from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pymysql.connections import Connection


from clearskies.configs import integer, string
from clearskies.cursors import base
from clearskies.decorators import parameters_to_properties


class Mysql(base.Base):
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
    ):
        self.finalize_and_validate_configuration()

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
        if self.environment.get("database_ssl_ca", True):
            self.ssl_ca = self.environment.get("database_ssl_ca")

    @property
    def connection(self) -> "Connection":
        """Return the connection for the cursor."""
        try:
            import pymysql
        except:
            raise ValueError(
                "The cursor requires pymysql to be installed.  This is an optional dependency of clearskies, so to include it do a `pip install 'clear-skies[mysql]'`"
            )

        return pymysql.connect(
            user=self.username,
            password=self.password,
            host=self.host,
            database=self.database_name,
            port=self.port,
            cursorclass=pymysql.cursors.DictCursor,
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
