from types import ModuleType

import clearskies.configs
from clearskies import decorators
from clearskies.cursors.cursor import Cursor


class Postgresql(Cursor):
    """
    A clearskies PostgreSQL cursor.

    This class provides a PostgreSQL cursor implementation with support for
    connection configuration, port forwarding, and SQL formatting.

    ### Configuration

    The following parameters are available (with their default values):

    - `hostname`: Hostname of the PostgreSQL server (`localhost`)
    - `username`: Username for authentication (`root`)
    - `password`: Password for authentication (`""`)
    - `database`: Name of the database (`example`)
    - `port`: Port number (defaults to 5432 if not specified)
    - `cert_path`: Path to SSL certificate (optional)
    - `autocommit`: Whether to autocommit transactions (`True`)
    - `connect_timeout`: Connection timeout in seconds (`2`)
    - `port_forwarding`: Optional port forwarding configuration (see below)

    ### Port Forwarding

    The `port_forwarding` parameter accepts an instance of a subclass of
    [`PortForwarder`](src/clearskies/cursors/port_forwarding/port_forwarder.py:1),
    enabling SSM or SSH-based port forwarding if required.

    #### Example

    ```python
    from clearskies.cursors.port_forwarding.ssm import SSMPortForwarder
    import clearskies

    cursor = clearskies.cursors.Postgresql(
        hostname="db.internal",
        username="admin",
        password="secret",
        database="mydb",
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
    Hostname of the PostgreSQL server.
    """
    hostname = clearskies.configs.String(default="localhost")

    """
    Username for authentication.
    """
    username = clearskies.configs.String(default="root")

    """
    Password for authentication.
    """
    password = clearskies.configs.String(default="")

    """
    Port number for the PostgreSQL server (defaults to 5432 if not specified).
    """
    port = clearskies.configs.Integer(default=None)

    """
    Default port number for the PostgreSQL server.
    """
    default_port = clearskies.configs.Integer(default=5432)

    """
    Path to SSL certificate (optional).
    """
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
        self.finalize_and_validate_configuration()

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
