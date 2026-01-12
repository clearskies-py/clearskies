from abc import ABC
from types import ModuleType
from typing import Protocol

import clearskies.configs
from clearskies import configurable, decorators, loggable
from clearskies.cursors.port_forwarding.port_forwarder import PortForwarder
from clearskies.di import InjectableProperties, inject


class DBAPICursor(Protocol):
    """
    A minimal protocol for a DB-API 2.0 cursor.

    This uses structural subtyping. Any object (like a real cursor
    or a mock) will match this type as long as it has the
    required attributes, even if it doesn't explicitly inherit
    from DBAPICursor.
    """

    def execute(self, sql: str, parameters: tuple | list):
        """Execute a SQL statement with parameters."""
        ...

    def close(self):
        """Close the cursor."""
        ...


class DBAPIConnection(Protocol):
    """
    A minimal protocol for a DB-API 2.0 connection.

    This uses structural subtyping. Any object (like a real connection
    or a mock) will match this type as long as it has the
    required attributes, even if it doesn't explicitly inherit
    from DBAPIConnection.
    """

    def cursor(self) -> DBAPICursor:
        """Return a cursor for this connection."""
        ...

    def close(self):
        """Close the connection."""
        ...


class Cursor(ABC, configurable.Configurable, InjectableProperties, loggable.Loggable):
    """
    A clearskies database cursor.

    This is the base class for all cursor implementations, providing a unified interface for
    database operations across different backends. It manages connection setup, query execution,
    and SQL formatting, and supports optional port forwarding.

    ### Port Forwarding

    The `port_forwarding` parameter accepts an instance of a subclass of
    [`PortForwarder`](src/clearskies/cursors/port_forwarding/port_forwarder.py:1).
    This enables flexible port forwarding strategies, such as SSM, SSH with certificate,
    or SSH with private key. Only SSM is implemented in this repository; others can be
    implemented as needed.

    #### Example: SSM Port Forwarding

    ```python
    from clearskies.cursors.port_forwarding.ssm import SSMPortForwarder
    import clearskies

    cursor = clearskies.cursors.from_environment.Mysql(
        database="example",
        port_forwarding=SSMPortForwarder(
            instance_id="i-1234567890abcdef0",
            region="eu-west-1",
        ),
    )
    cursor.execute("SELECT * FROM table")
    results = cursor.fetchall()
    ```

    ### Attributes

    - `database`: Name of the database to connect to.
    - `autocommit`: Whether to automatically commit transactions.
    - `port_forwarding`: Optional port forwarding configuration (PortForwarder subclass).
    - `connect_timeout`: Connection timeout in seconds.
    - `table_escape_character`: Character used to escape table names.
    - `column_escape_character`: Character used to escape column names.
    - `value_placeholder`: Placeholder character for parameter binding.
    """

    """
    Name of the database to connect to.
    """
    database = clearskies.configs.String(default="example")

    """
    Whether to automatically commit transactions.
    """
    autocommit = clearskies.configs.Boolean(default=True)

    """
    Optional port forwarding configuration (can be a PortForwarder instance).
    """
    port_forwarding = clearskies.configs.Any(default=None)

    """
    Connection timeout in seconds.
    """
    connect_timeout = clearskies.configs.Integer(default=2)

    """Dependency injection container.a"""
    di = inject.Di()

    table_escape_character = "`"
    column_escape_character = "`"
    value_placeholder = "%s"
    _cursor: DBAPICursor
    _factory: ModuleType
    _connection: DBAPIConnection
    _port_forwarder_active = False

    @decorators.parameters_to_properties
    def __init__(
        self,
        database="example",
        autocommit=True,
        port_forwarding=None,
        connect_timeout=2,
    ):
        self._di = None  # Ensure _di exists to avoid AttributeError
        self.finalize_and_validate_configuration()

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor."""
        return self._factory

    def build_connection_kwargs(self) -> dict:
        """Return the connection kwargs for the cursor."""
        return {
            "database": self.database,
            "autocommit": self.autocommit,
            "connect_timeout": self.connect_timeout,
        }

    @property
    def cursor(self) -> DBAPICursor:
        """Get or create a database cursor instance."""
        if hasattr(self, "_cursor"):
            return self._cursor

        connection_kwargs = self.build_connection_kwargs()

        if self.port_forwarding:
            if not isinstance(self.port_forwarding, PortForwarder):
                raise TypeError(f"port_forwarding must be a PortForwarder instance, got {type(self.port_forwarding)}")

            self.logger.info("Establishing port forwarding...")
            try:
                # Get original host/port from connection kwargs
                original_host = connection_kwargs.get("host", "localhost")
                original_port = connection_kwargs.get(
                    "port", self.default_port if hasattr(self, "default_port") else 3306
                )

                # Setup port forwarding and get local endpoint
                if hasattr(self.port_forwarding, "injectable_properties"):
                    self.port_forwarding.injectable_properties(di=self.di)
                local_host, local_port = self.port_forwarding.setup(original_host, original_port)

                # Update connection kwargs to use local endpoint
                connection_kwargs["host"] = local_host
                connection_kwargs["port"] = local_port

                self._port_forwarder_active = True

            except Exception as e:
                self.logger.error(f"Port forwarding failed: {e}")
                raise

        self._connection = self.factory.connect(
            **connection_kwargs,
        )
        self._cursor = self._connection.cursor()

        return self._cursor

    def close(self) -> None:
        """Close cursor, connection, and port forwarding."""
        if hasattr(self, "_cursor"):
            self._cursor.close()
            delattr(self, "_cursor")

        if hasattr(self, "_connection"):
            self._connection.close()
            delattr(self, "_connection")

        if self._port_forwarder_active and self.port_forwarding:
            self.port_forwarding.teardown()
            self._port_forwarder_active = False

    def __del__(self):
        """Ensure cleanup on object destruction."""
        try:
            self.close()
        except Exception:
            pass

    def __call__(self, *args: configurable.Any, **kwds: configurable.Any) -> configurable.Any:
        return self.cursor

    def __iter__(self):
        """Allow direct iteration over the cursor config."""
        return iter(self())

    def __next__(self):
        """Allow direct next() calls on the cursor config."""
        return next(self())

    def column_equals_with_placeholder(self, column_name: str) -> str:
        """
        Generate SQL for a column equality check with placeholder.

        Args:
            column_name: Name of the column to check.

        Returns
        -------
            SQL string in format: `column`=%s
        """
        return f"{self.column_escape_character}{column_name}{self.column_escape_character}={self.value_placeholder}"

    def as_sql_with_placeholders(self, table: str, column: str, operator: str, number_values: int = 1) -> str | None:
        """
        Generate SQL condition with placeholders.

        Args:
            table: Table name.
            column: Column name.
            operator: SQL operator (e.g., '=', '>', '<').
            number_values: Number of value placeholders needed.

        Returns
        -------
            SQL string if number_values is 1, None otherwise.
        """
        if number_values == 1:
            return f"{table}.{column} {operator} {self.value_placeholder}"
        return None

    def execute(self, sql: str, parameters: tuple | list = ()):
        """
        Execute a SQL statement with parameters.

        Args:
            sql: SQL statement to execute.
            parameters: Parameters for the SQL statement.

        Returns
        -------
            Result of cursor.execute().
        """
        try:
            self.logger.debug(f"Executing SQL: {sql} with parameters: {parameters}")
            return self.cursor.execute(sql, parameters)
        except Exception:
            self.logger.exception(f"Error executing SQL: {sql} with parameters: {parameters}")
            raise

    @property
    def lastrowid(self) -> int | None:
        """
        Get the last inserted row ID from the most recent INSERT operation.

        The DB-API 2.0 standard specifies that `lastrowid` should be available
        on the cursor object. However, some implementations (e.g., pymysql) expose
        this as `connection.insert_id()` instead.

        Returns
        -------
            int | None: The last inserted row ID, or None if unavailable.

        Notes
        -----
            Fallback strategy:
            1. Check cursor.lastrowid (DB-API 2.0 standard)
            2. Check connection.insert_id() (pymysql compatibility)
        """
        cursor_lastrowid = getattr(self.cursor, "lastrowid", None)
        if cursor_lastrowid:
            return cursor_lastrowid

        # Fallback for pymysql which uses connection.insert_id()
        if hasattr(self, "_connection"):
            connection_insert_id = getattr(self._connection, "insert_id", None)
            if callable(connection_insert_id):
                return connection_insert_id()
            return connection_insert_id

        return None
