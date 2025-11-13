import re
from abc import ABC
from collections.abc import Callable, Iterator
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


class CursorProxy:
    """
    A transparent proxy for DB-API 2.0 cursors that intercepts execute() calls.

    This proxy wraps a DB-API cursor and intercepts execute() and executemany()
    calls to format SQL parameters according to the database's parameter style
    (e.g., converting %s to ? for SQLite's qmark style). All other cursor
    operations are transparently delegated to the underlying cursor.

    The proxy implements the full iterator protocol, allowing code like:
        for row in cursor:
            process(row)

    It also provides transparent access to all cursor attributes like:
        cursor.description
        cursor.rowcount
        cursor.lastrowid

    Args:
        cursor: The underlying DB-API cursor to wrap
        format_func: Function that takes (sql, params) and returns
                    (formatted_sql, formatted_params)

    Example:
        >>> def my_format(sql, params):
        ...     return sql.replace("%s", "?"), params
        >>> raw_cursor = connection.cursor()
        >>> proxy = CursorProxy(raw_cursor, my_format)
        >>> proxy.execute("SELECT * FROM users WHERE id=%s", (123,))
        >>> for row in proxy:
        ...     print(row)
    """

    def __init__(
        self,
        cursor: Any,
        format_func: Callable[[str, Any], tuple[str, Any]],
    ) -> None:
        """Initialize the cursor proxy."""
        # Use object.__setattr__ to avoid triggering __setattr__
        object.__setattr__(self, "_cursor", cursor)
        object.__setattr__(self, "_format_func", format_func)

    def execute(self, sql: str, params: Any = None) -> Any:
        """
        Execute SQL with parameter formatting.

        Args:
            sql: The SQL query string
            params: Parameters for the query (dict, list, or tuple)

        Returns
        -------
            The result of the cursor's execute method
        """
        if params is None or (isinstance(params, (list, tuple, dict)) and len(params) == 0):
            return self._cursor.execute(sql)

        formatted_sql, formatted_params = self._format_func(sql, params)
        return self._cursor.execute(formatted_sql, formatted_params)

    def executemany(self, sql: str, seq_of_params: list[Any]) -> Any:
        """
        Execute SQL multiple times with parameter formatting.

        Args:
            sql: The SQL query string
            seq_of_params: Sequence of parameter sets

        Returns
        -------
            The result of the cursor's executemany method
        """
        if not seq_of_params:
            return self._cursor.executemany(sql, seq_of_params)

        formatted_params_list = []
        formatted_sql = None

        for params in seq_of_params:
            formatted_sql, formatted_params = self._format_func(sql, params)
            formatted_params_list.append(formatted_params)

        return self._cursor.executemany(formatted_sql, formatted_params_list)

    def __iter__(self) -> Iterator:
        """
        Support iteration over result rows.

        Returns
        -------
            Iterator over the cursor's results
        """
        return iter(self._cursor)

    def __next__(self) -> Any:
        """
        Support next() calls for iteration.

        Returns
        -------
            The next row from the cursor

        Raises
        ------
            StopIteration: When there are no more rows
        """
        return next(self._cursor)

    def __getattr__(self, name: str) -> Any:
        """
        Delegate all other attributes to the underlying cursor.

        This provides transparent access to cursor attributes like:
        - description: Column metadata
        - rowcount: Number of affected rows
        - lastrowid: Last inserted row ID
        - arraysize: Default fetchmany size
        - fetchone(): Fetch a single row
        - fetchall(): Fetch all rows
        - fetchmany(): Fetch multiple rows
        - close(): Close the cursor
        - etc.

        Args:
            name: The attribute name to access

        Returns
        -------
            The attribute value from the underlying cursor
        """
        return getattr(self._cursor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Set attributes on the underlying cursor.

        Args:
            name: The attribute name to set
            value: The value to set
        """
        if name in ("_cursor", "_format_func"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._cursor, name, value)

    def __enter__(self):
        """
        Support context manager protocol if cursor supports it.

        Returns
        -------
            The proxy itself for context manager usage
        """
        if hasattr(self._cursor, "__enter__"):
            self._cursor.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Support context manager protocol if cursor supports it.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns
        -------
            The result of the cursor's __exit__ method, if it exists
        """
        if hasattr(self._cursor, "__exit__"):
            return self._cursor.__exit__(exc_type, exc_val, exc_tb)
        return None

    def __repr__(self) -> str:
        """Return a string representation of the proxy."""
        return f"<CursorProxy wrapping {self._cursor!r}>"


# Our "standard" input format is a dictionary of named parameters
T_NamedParams = dict[str, Any]

# The "native" output format can be a dict (for pyformat/named)
# or a list (for qmark/format)
T_NativeParams = dict[str, Any] | list[Any] | tuple[Any, ...]


class BaseCursor(ABC, configurable.Configurable, injectable_properties.InjectableProperties):
    """Abstract base class for database cursors."""

    # DB-API 2.0 cursor interface members that should be delegated to the proxy
    _CURSOR_API_MEMBERS = frozenset(
        {
            "execute",
            "executemany",
            "fetchone",
            "fetchall",
            "fetchmany",
            "close",
            "description",
            "rowcount",
            "lastrowid",
            "arraysize",
            "callproc",
            "nextset",
            "setinputsizes",
            "setoutputsize",
            "scroll",
            "messages",
            "rownumber",
        }
    )

    cursor_type: str
    environment = inject.Environment()
    sys: ModuleType = inject.ByName("sys")  # type: ignore
    database_name = string.String(default=None)
    autocommit = boolean.Boolean(default=True)
    parameter_style = string.String(required=False, default="format")
    _cursor: DBAPICursor
    _factory: ModuleType

    @parameters_to_properties
    def __init__(
        self, database_name: str | None = None, autocommit: bool | None = None, parameter_style: str | None = None
    ):
        self.finalize_and_validate_configuration()

    def configure(self) -> None:
        """Configure the cursor from environment if available."""
        # Check if environment has been injected (may not be if cursor created directly)
        try:
            environment = object.__getattribute__(self, "environment")
        except AttributeError:
            # Environment not injected, skip configuration from environment
            return

        # Get database_name from environment if not provided
        if not self.database_name:
            try:
                self.database_name = environment.get("database_name")
            except KeyError:
                raise ValueError(
                    "Database name must be provided either via parameter or environment variable 'database_name'."
                )

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

    def __call__(self) -> "CursorProxy":
        """
        Return a cursor proxy that wraps the DB-API cursor.

        This method creates and caches a cursor proxy. Subsequent calls return
        the cached proxy. Use this to access the cursor directly as a function call.
        """
        # Use object.__getattribute__ to avoid triggering __getattr__ and causing recursion
        try:
            return object.__getattribute__(self, "_cursor_proxy")
        except AttributeError:
            with self.connection as conn:
                raw_cursor = conn.cursor()
                proxy = CursorProxy(raw_cursor, self.format)
                object.__setattr__(self, "_cursor_proxy", proxy)
                return proxy

    def __getattr__(self, name: str) -> Any:
        """
        Delegate cursor operations to the proxy when accessed directly.

        This allows cursor configs to be used directly as cursors:
            cursor = SqliteCursor()
            cursor.execute("SELECT * FROM table")  # Works!
            for row in cursor:  # Works!
                print(row)

        Note: This is only called when normal attribute resolution fails.
        """
        # Don't delegate Python special methods (dunder methods)
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        # Only delegate DB-API 2.0 cursor operations to the proxy
        if name in self._CURSOR_API_MEMBERS:
            return getattr(self(), name)

        # Not a cursor API member - re-raise AttributeError
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __iter__(self):
        """
        Allow direct iteration over the cursor config.

        This is explicitly defined because __getattr__ rejects dunder methods.
        """
        return iter(self())

    def __next__(self):
        """
        Allow direct next() calls on the cursor config.

        This is explicitly defined because __getattr__ rejects dunder methods.
        """
        return next(self())

    @property
    def parameter_style_resolved(self) -> str:
        """Return the parameter style for the cursor, resolving from factory if not explicitly set."""
        if self.parameter_style:
            return self.parameter_style

        paramstyle: Any = getattr(self.factory, "paramstyle", None)
        if not isinstance(paramstyle, str):
            raise TypeError(  # noqa: TRY003
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
