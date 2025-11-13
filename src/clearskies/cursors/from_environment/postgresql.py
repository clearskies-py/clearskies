import clearskies.configs
from clearskies import decorators
from clearskies.cursors.postgresql import Postgresql as PostgresqlBase
from clearskies.di import inject


class Postgresql(PostgresqlBase):
    hostname_environment_key = clearskies.configs.String(default="DATABASE_HOST")
    username_environment_key = clearskies.configs.String(default="DATABASE_USERNAME")
    password_environment_key = clearskies.configs.String(default="DATABASE_PASSWORD")
    database_environment_key = clearskies.configs.String(default="DATABASE_NAME")

    port_environment_key = clearskies.configs.String(default="DATABASE_PORT")
    cert_path_environment_key = clearskies.configs.String(default="DATABASE_CERT_PATH")
    autocommit_environment_key = clearskies.configs.String(default="DATABASE_AUTOCOMMIT")
    connect_timeout_environment_key = clearskies.configs.String(default="DATABASE_CONNECT_TIMEOUT")

    environment = inject.Environment()

    @decorators.parameters_to_properties
    def __init__(
        self,
        hostname_environment_key="DATABASE_HOST",
        username_environment_key="DATABASE_USERNAME",
        password_environment_key="DATABASE_PASSWORD",
        database_environment_key="DATABASE_NAME",
        port_environment_key="DATABASE_PORT",
        cert_path_environment_key="DATABASE_CERT_PATH",
        autocommit_environment_key="DATABASE_AUTOCOMMIT",
        port_forwarding=None,
    ):
        pass

    def build_connection_kwargs(self) -> dict:
        connection_kwargs = {
            "user": self.environment.get(self.username_environment_key),
            "password": self.environment.get(self.password_environment_key),
            "host": self.environment.get(self.hostname_environment_key),
            "database": self.environment.get(self.database_environment_key),
            "port": self.environment.get(self.port_environment_key, silent=True),
            "sslcert": self.environment.get(self.cert_path_environment_key, silent=True),
            "connect_timeout": self.environment.get(self.connect_timeout_environment_key, silent=True),
        }

        for kwarg in ["autocommit", "connect_timeout", "port", "sslcert"]:
            if not connection_kwargs[kwarg]:
                del connection_kwargs[kwarg]

        return {**super().build_connection_kwargs(), **connection_kwargs}
