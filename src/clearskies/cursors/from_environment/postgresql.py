from collections.abc import Callable

import clearskies.configs
from clearskies import decorators
from clearskies.cursors.postgresql import Postgresql as PostgresqlBase
from clearskies.di import inject


class Postgresql(PostgresqlBase):
    """
    A clearskies PostgreSQL cursor configured from environment variables.

    This class provides a PostgreSQL cursor implementation that reads connection parameters
    from environment variables, making it easy to configure for different environments.
    It supports all features of the base [`Postgresql`](src/clearskies/cursors/postgresql.py:1) class,
    including port forwarding via the `port_forwarding` parameter.

    ### Environment Variable Keys

    The following environment variables are used by default (can be overridden):

    - `DATABASE_HOST`: Hostname of the PostgreSQL server.
    - `DATABASE_USERNAME`: Username for authentication.
    - `DATABASE_PASSWORD`: Password for authentication.
    - `DATABASE_NAME`: Name of the database.
    - `DATABASE_PORT`: Port number (optional).
    - `DATABASE_CERT_PATH`: Path to SSL certificate (optional).
    - `DATABASE_AUTOCOMMIT`: Autocommit setting (optional).
    - `DATABASE_CONNECT_TIMEOUT`: Connection timeout (optional).

    ### Port Forwarding

    The `port_forwarding` parameter accepts an instance of a subclass of
    [`PortForwarder`](src/clearskies/cursors/port_forwarding/port_forwarder.py:1),
    enabling SSM or SSH-based port forwarding if required.

    #### Example

    ```python
    from clearskies.cursors.port_forwarding.ssm import SSMPortForwarder
    import clearskies

    cursor = clearskies.cursors.from_environment.Postgresql(
        port_forwarding=SSMPortForwarder(
            instance_id="i-1234567890abcdef0",
            region="eu-west-1",
        ),
    )
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
    ```

    """

    """
    Environment variable key for the PostgreSQL server hostname.
    """
    hostname_environment_key = clearskies.configs.String(default="DATABASE_HOST")

    """
    Environment variable key for the PostgreSQL username.
    """
    username_environment_key = clearskies.configs.String(default="DATABASE_USERNAME")

    """
    Environment variable key for the PostgreSQL password.
    """
    password_environment_key = clearskies.configs.String(default="DATABASE_PASSWORD")

    """
    Environment variable key for the database name.
    """
    database_environment_key = clearskies.configs.String(default="DATABASE_NAME")

    """
    Environment variable key for the PostgreSQL server port (optional).
    """
    port_environment_key = clearskies.configs.String(default="DATABASE_PORT")

    """
    Environment variable key for the SSL certificate path (optional).
    """
    cert_path_environment_key = clearskies.configs.String(default="DATABASE_CERT_PATH")

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
        hostname_environment_key: str | None = "DATABASE_HOST",
        username_environment_key: str | None = "DATABASE_USERNAME",
        password_environment_key: str | None = "DATABASE_PASSWORD",
        database_environment_key: str | None = "DATABASE_NAME",
        port_environment_key: str | None = "DATABASE_PORT",
        cert_path_environment_key: str | None = "DATABASE_CERT_PATH",
        autocommit_environment_key: str | None = "DATABASE_AUTOCOMMIT",
        port_forwarding: Callable | None = None,
    ):
        self.finalize_and_validate_configuration()

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
