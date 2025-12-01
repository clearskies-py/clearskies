from sqlite3 import Cursor as SQLiteCursor
from types import ModuleType

import clearskies.configs
from clearskies.cursors.cursor import Cursor
from clearskies.di import inject


class Sqlite(Cursor):
    database = clearskies.configs.String(default="example.db")
    connect_timeout = clearskies.configs.Float(default=2.0)  # type: ignore[assignment]
    value_placeholder = "?"
    sys = inject.ByName("sys")

    def __init__(
        self,
        database="example.db",
        autocommit=True,
        connect_timeout=2.0,
    ):
        self.autocommit = autocommit
        self.database = database
        self.connect_timeout = connect_timeout

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
    def cursor(self) -> SQLiteCursor:
        """Get or create a database cursor instance."""
        if not hasattr(self, "_cursor"):

            def dict_factory(cursor, row):
                fields = [column[0] for column in cursor.description]
                return dict(zip(fields, row))

            connection = self.factory.connect(
                database=self.database,
                timeout=2.0,
            )
            connection.row_factory = dict_factory
            if self.autocommit:
                connection.isolation_level = None  # Enable autocommit for sqlite3
            else:
                if self.sys.version_info > (3, 12):  # noqa: UP036
                    connection.autocommit = False
                else:
                    connection.isolation_level = "DEFERRED"  # Disable autocommit
            self._cursor = connection.cursor()
        return self._cursor  # type: ignore[return-value]
