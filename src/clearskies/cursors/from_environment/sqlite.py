import clearskies.configs
from clearskies import decorators
from clearskies.cursors.sqlite import Sqlite as SqliteBase
from clearskies.di import inject


class Sqlite(SqliteBase):
    """
    A clearskies SQLite cursor configured from environment variables.

    This class provides a SQLite cursor implementation that reads connection parameters
    from environment variables, making it easy to configure for different environments.
    It supports all features of the base [`Sqlite`](src/clearskies/cursors/sqlite.py:1) class.

    ### Environment Variable Keys

    The following environment variables are used by default (can be overridden):

    - `DATABASE_NAME`: Path or name of the SQLite database file.
    - `DATABASE_AUTOCOMMIT`: Autocommit setting (optional).
    - `DATABASE_CONNECT_TIMEOUT`: Connection timeout (optional).

    #### Example

    ```python
    import clearskies

    cursor = clearskies.cursors.from_environment.Sqlite()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
    ```

    """

    """
    Environment variable key for the SQLite database file path or name.
    """
    database_environment_key = clearskies.configs.String(default="DATABASE_NAME")

    """
    Environment variable key for the autocommit setting (optional).
    """
    autocommit_environment_key = clearskies.configs.String(default="DATABASE_AUTOCOMMIT")

    """
    Environment variable key for the connection timeout (optional).
    """
    connect_timeout_environment_key = clearskies.configs.String(default="DATABASE_CONNECT_TIMEOUT")

    environment = inject.Environment()

    @decorators.parameters_to_properties
    def __init__(
        self,
        database_environment_key="DATABASE_NAME",
        autocommit_environment_key="DATABASE_AUTOCOMMIT",
        connect_timeout_environment_key="DATABASE_CONNECT_TIMEOUT",
    ):
        self.finalize_and_validate_configuration()

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
