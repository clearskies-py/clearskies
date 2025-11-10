import re
from abc import ABC
from types import ModuleType
from typing import Any, Protocol

from clearskies import configurable
from clearskies.configs import boolean, string
from clearskies.decorators import parameters_to_properties
from clearskies.di import inject, injectable_properties


class DBAPICursor(Protocol):
    """
    A minimal protocol for a DB-API 2.0 cursor.

    This uses structural subtyping. Any object (like a real cursor
    or a mock) will match this type as long as it has the
    required attributes, even if it doesn't explicitly inherit
    from DBAPICursor.

    Since we only introspect its class, this protocol is empty.
    We're just using it as a "marker" type for clarity.
    """

    pass


# Our "standard" input format is a dictionary of named parameters
T_NamedParams = dict[str, Any]

# The "native" output format can be a dict (for pyformat/named)
# or a list (for qmark/format)
T_NativeParams = dict[str, Any] | list[Any] | tuple[Any, ...]


class BaseCursor(ABC, configurable.Configurable, injectable_properties.InjectableProperties):
    """Abstract base class for database cursors."""

    cursor_type: str
    environment = inject.Environment()
    sys: ModuleType = inject.ByName("sys")  # type: ignore
    database_name = string.String(default=None)
    autocommit = boolean.Boolean(default=True)
    parameter_style = string.String(required=False, default=None)
    _factory: ModuleType

    @parameters_to_properties
    def __init__(
        self, database_name: str | None = None, autocommit: bool | None = None, parameter_style: str | None = None
    ):
        pass

    def configure(self) -> None:
        """Configure the cursor."""
        try:
            if not self.database_name:
                self.database_name = self.environment.get("database_name")
        except KeyError:
            raise ValueError(
                "Database name must be provided either via parameter or environment variable 'database_name'."
            )

    def finalize_and_validate_configuration(self) -> None:
        """Finalize and validate the configuration."""
        self.configure()
        print("Finalizing and validating configuration for cursor type:", self.cursor_type)
        super().finalize_and_validate_configuration()

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor. Subclasses must override this property with a strongly typed module."""
        raise NotImplementedError("Subclasses must implement the factory property and return the correct module.")

    @property
    def backend_type(self) -> str:
        """Return the type of cursor backend."""
        return self.cursor_type

    @property
    def connection(self) -> Any:
        """Return the connection for the cursor."""
        raise NotImplementedError("Subclasses must implement connection property.")

    @property
    def connection_details(self) -> dict[str, str]:
        """Return the connection details for the cursor."""
        raise NotImplementedError("Subclasses must implement connection_details property.")

    def __call__(self) -> "DBAPICursor":
        """Return the cursor instance."""
        with self.connection as conn:
            cursor = conn.cursor()
            return cursor

    def cursor(self) -> "DBAPICursor":
        """Return the cursor instance."""
        with self.connection as conn:
            cursor = conn.cursor()
            return cursor

    def execute(self, sql: str, params: T_NamedParams) -> Any:
        """Execute a query with the given parameters."""
        with self.connection as conn:
            with conn.cursor() as cursor:
                reformatted_sql, reformatted_params = self.format(sql, params)
                cursor.execute(reformatted_sql, reformatted_params)
                return cursor

    @property
    def lastrowid(self) -> Any:
        """Return the last inserted row ID."""
        with self.connection as conn:
            return conn.insert_id()

    @property
    def parameter_style_resolved(self) -> str:
        """Return the parameter style for the cursor, resolving from factory if not explicitly set."""
        if self.parameter_style:
            return self.parameter_style

        paramstyle: Any = getattr(self.factory, "paramstyle", None)
        if not isinstance(paramstyle, str):
            raise AttributeError(
                f"Factory module '{self.factory.__name__}' does not have a valid 'paramstyle' attribute."
            )

        return paramstyle

    def format(self, sql: str, params: T_NamedParams) -> tuple[str, T_NativeParams]:
        """
        Translate %s to ? ONLY if the driver is 'qmark'.

        Otherwise, passes the query through unchanged.
        """
        if self.parameter_style_resolved == "qmark":
            reformatted_sql = re.sub(r"%s", "?", sql)
            return reformatted_sql, params

        # For 'format' (pymysql) and 'pyformat' (psycopg),
        # we pass the %s query and list/tuple params directly.
        return sql, params
