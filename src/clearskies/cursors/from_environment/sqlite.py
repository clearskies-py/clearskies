import clearskies.configs
from clearskies import decorators
from clearskies.cursors.sqlite import Sqlite as SqliteBase
from clearskies.di import inject


class Sqlite(SqliteBase):
    database_environment_key = clearskies.configs.String(default="DATABASE_NAME")
    autocommit_environment_key = clearskies.configs.String(default="DATABASE_AUTOCOMMIT")
    connect_timeout_environment_key = clearskies.configs.String(default="DATABASE_CONNECT_TIMEOUT")

    environment = inject.Environment()

    @decorators.parameters_to_properties
    def __init__(
        self,
        database_environment_key="DATABASE_NAME",
        autocommit_environment_key="DATABASE_AUTOCOMMIT",
        connect_timeout_environment_key="DATABASE_CONNECT_TIMEOUT",
    ):
        pass

    def build_connection_kwargs(self) -> dict:
        connection_kwargs = {
            "database": self.environment.get(self.database_environment_key),
            "autocommit": self.environment.get(self.autocommit_environment_key, silent=True),
            "connect_timeout": self.environment.get(self.connect_timeout_environment_key, silent=True),
        }

        for kwarg in ["autocommit", "connect_timeout"]:
            if not connection_kwargs[kwarg]:
                del connection_kwargs[kwarg]
            del connection_kwargs["connect_timeout"]

        return {**super().build_connection_kwargs(), **connection_kwargs}
