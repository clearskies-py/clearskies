from abc import ABC
from types import ModuleType
from typing import Protocol

import clearskies.configs
from clearskies import configurable, decorators, loggable
from clearskies.di import InjectableProperties


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


class Cursor(ABC, configurable.Configurable, InjectableProperties, loggable.Loggable):
    """
    Abstract base class for database cursor implementations.

    Provides a common interface for database operations across different
    database backends. Handles connection management, query execution,
    and SQL formatting with configurable escape characters and placeholders.

    Attributes
    ----------
        database: Name of the database to connect to.
        autocommit: Whether to automatically commit transactions.
        port_forwarding: Optional port forwarding configuration.
        connect_timeout: Connection timeout in seconds.
        table_escape_character: Character used to escape table names.
        column_escape_character: Character used to escape column names.
        value_placeholder: Placeholder character for parameter binding.
    """

    socket = clearskies.di.inject.Socket()
    subprocess = clearskies.di.inject.Subprocess()

    database = clearskies.configs.String(default="example")
    autocommit = clearskies.configs.Boolean(default=True)
    port_forwarding = clearskies.configs.Any(default=None)
    connect_timeout = clearskies.configs.Integer(default=2)

    table_escape_character = "`"
    column_escape_character = "`"
    value_placeholder = "%s"
    _cursor: DBAPICursor
    _factory: ModuleType
    _connection: DBAPIConnection

    @decorators.parameters_to_properties
    def __init__(
        self,
        database="example",
        autocommit=True,
        port_forwarding=None,
        connect_timeout=2,
    ):
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
        if not hasattr(self, "_cursor"):
            if self.port_forwarding:
                self.logger.info("Establishing port forwarding...")
                try:
                    forwarded = self.port_forwarding_context()
                    if not forwarded:
                        raise ValueError("Port forwarding context did not yield forwarded ports.")
                except Exception as e:
                    self.logger.error(f"Port forwarding failed: {e}")
                    raise

            self._connection = self.factory.connect(
                **self.build_connection_kwargs(),
            )
            self._cursor = self._connection.cursor()

        return self._cursor

    def __call__(self, *args: configurable.Any, **kwds: configurable.Any) -> configurable.Any:
        return self.cursor

    def __iter__(self):
        """Allow direct iteration over the cursor config."""
        return iter(self())

    def __next__(self):
        """Allow direct next() calls on the cursor config."""
        return next(self())

    def port_forwarding_context(self):
        """Context manager for port forwarding (if applicable)."""
        raise NotImplementedError("Port forwarding not implemented for this cursor.")

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
