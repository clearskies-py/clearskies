from types import ModuleType

import clearskies.configs
from clearskies import decorators
from clearskies.cursors.cursor import Cursor


class Postgresql(Cursor):
    hostname = clearskies.configs.String(default="localhost")
    username = clearskies.configs.String(default="root")
    password = clearskies.configs.String(default="")
    port = clearskies.configs.Integer(default=None)
    default_port = clearskies.configs.Integer(default=5432)
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

    def build_connection_kwargs(self) -> dict:
        connection_kwargs = {
            "user": self.username,
            "password": self.password,
            "host": self.hostname,
            "port": self.port,
            "ssl_ca": self.cert_path,
            "sslcert": self.cert_path,
            "row_factory": self.factory.rows.dict_row,
        }
        if not connection_kwargs["sslcert"]:
            del connection_kwargs["sslcert"]

        if not connection_kwargs["port"]:
            connection_kwargs["port"] = self.default_port

        return {**super().build_connection_kwargs(), **connection_kwargs}
