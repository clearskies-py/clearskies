from sqlite3 import Connection as SQLiteConnection
from sqlite3 import Cursor as SQLiteCursor
from types import ModuleType
from typing import cast

from clearskies import configs
from clearskies.cursors.cursor import Cursor
from clearskies.di import inject


class Sqlite(Cursor):
    """
    A clearskies SQLite cursor.

    This class provides a SQLite cursor implementation with support for
    connection configuration and SQL formatting.

    ### Configuration

    The following parameters are available (with their default values):

    - `database`: Path or name of the SQLite database file (`example.db`)
    - `autocommit`: Whether to autocommit transactions (`True`)
    - `connect_timeout`: Connection timeout in seconds (`2.0`)

    #### Example

    ```python
    import clearskies

    cursor = clearskies.cursors.Sqlite(
        database="example.db",
        autocommit=True,
        connect_timeout=2.0,
    )
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
    ```
    """

    """
    Path or name of the SQLite database file.
    """
    database = configs.String(default="example.db")

    """
    Connection timeout in seconds.
    """
    connect_timeout = configs.Float(default=2.0)  # type: ignore[assignment]
    value_placeholder = "?"
    sys = inject.ByName("sys")

    def __init__(
        self,
        database: str = "example.db",
        autocommit: bool = True,
        connect_timeout: float = 2.0,
    ):
        self.autocommit = autocommit
        self.database = database
        self.connect_timeout = connect_timeout
        self.finalize_and_validate_configuration()

    @property
    def factory(self) -> ModuleType:
        """Return the factory for the cursor."""
        if not hasattr(self, "_factory"):
            try:
                import sqlite3

                self._factory = sqlite3
            except ImportError as e:
                raise ValueError(  # noqa: TRY003
                    "The cursor requires sqlite3 to be available. sqlite3 is included with the standard library for Python, "
                    f"so this error likely indicates a misconfigured Python installation. Error: {e}"
                ) from e
        return self._factory

    @property
    def connection(self) -> SQLiteConnection:
        """Get or create a database connection instance."""
        if hasattr(self, "_connection"):
            return cast(SQLiteConnection, self._connection)

        def dict_factory(cursor, row):
            fields = [column[0] for column in cursor.description]
            return dict(zip(fields, row))

        self._connection: SQLiteConnection = cast(
            SQLiteConnection,
            self.factory.connect(
                database=self.database,
                timeout=self.connect_timeout,
            ),
        )
        self._connection.row_factory = dict_factory
        if self.autocommit:
            self._connection.isolation_level = None  # Enable autocommit for sqlite3
        else:
            if self.sys.version_info > (3, 12):  # noqa: UP036
                self._connection.autocommit = False  # type: ignore[attr-defined]
            else:
                self._connection.isolation_level = "DEFERRED"  # Disable autocommit
        return self._connection  # type: ignore[return-value]

    @property
    def cursor(self) -> SQLiteCursor:
        """Get or create a database cursor instance."""
        if not hasattr(self, "_cursor"):
            self._cursor = self.connection.cursor()
        return self._cursor  # type: ignore[return-value]
