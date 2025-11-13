from types import ModuleType

import clearskies.configs
from clearskies import decorators
from clearskies.cursors.cursor import Cursor


class Mysql(Cursor):
    hostname = clearskies.configs.String(default="localhost")
    username = clearskies.configs.String(default="root")
    password = clearskies.configs.String(default="")
    port = clearskies.configs.Integer(default=None)
    default_port = clearskies.configs.Integer(default=3306)
    cert_path = clearskies.configs.String(default=None)

    @decorators.parameters_to_properties
    def __init__(
        self,
        hostname="localhost",
        username="root",
        password="",
        database="example",
        autocommit=True,
        connect_timeout=2,
        port=None,
        cert_path=None,
        port_forwarding=None,
    ):
        pass

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor."""
        if not hasattr(self, "_factory"):
            try:
                import pymysql

                self._factory = pymysql
            except ImportError:
                raise ValueError(
                    "The cursor requires pymysql to be installed.  This is an optional dependency of clearskies, so to include it do a `pip install 'clear-skies[mysql]'`"
                )
        return self._factory

    def build_connection_kwargs(self) -> dict:
        connection_kwargs = {
            "user": self.username,
            "password": self.password,
            "host": self.hostname,
            "port": self.port,
            "ssl_ca": self.cert_path,
            "autocommit": self.autocommit,
            "cursorclass": self.factory.cursors.DictCursor,
        }
        if not connection_kwargs["ssl_ca"]:
            del connection_kwargs["ssl_ca"]

        if not connection_kwargs["port"]:
            connection_kwargs["port"] = self.default_port

        return {**super().build_connection_kwargs(), **connection_kwargs}
