from __future__ import annotations

from typing import TYPE_CHECKING

from clearskies.backends import cursor_backend
from clearskies.di import inject

if TYPE_CHECKING:
    pass


class SqliteBackend(cursor_backend.CursorBackend):
    """
    The cursor backend connects your models to a SQLite database.

    ## Installing Dependencies

    SQLite is included with Python's standard library, so no additional installation is required.

    ## Connecting to your database

    By default, the database file path is expected in an environment variable:

    | Name            | Default    | Value                                                         |
    |------------------|------------|---------------------------------------------------------------|
    | DATABASE_NAME    | :memory:   | The path to the SQLite database file, or ':memory:' for in-memory database |

    You can also provide the database name directly:

    ```python
    import clearskies


    class Product(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.SqliteBackend()
        id = clearskies.columns.Integer()
        name = clearskies.columns.String()


    # Use in-memory database
    cursor = clearskies.cursors.SqliteCursor(database_name=":memory:")

    # Or use a file-based database
    cursor = clearskies.cursors.SqliteCursor(database_name="/path/to/database.db")
    ```

    ## Connecting models to tables

    The table name for your model comes from calling the `destination_name` class method of the model class.  By
    default, this takes the class name, converts it to snake case, and then pluralizes it.  So, if you have a model
    class named `UserPreference` then the cursor backend will look for a table called `user_preferences`.  If this
    isn't what you want, then you can simply override `destination_name` to return whatever table you want:

    ```python
    class UserPreference(clearskies.Model):
        @classmethod
        def destination_name(cls):
            return "some_other_table_name"
    ```

    Additionally, the cursor backend accepts an argument called `table_prefix` which, if provided, will be prefixed
    to your table name.  Finally, you can declare a dependency called `global_table_prefix` which will automatically
    be added to every table name.  In the following example, the table name will be `user_configuration_preferences`
    due to:

     1. The `destination_name` method sets the table name to `preferences`
     2. The `table_prefix` argument to the SqliteBackend constructor adds a prefix of `configuration_`
     3. The `global_table_prefix` binding sets a prefix of `user_`, which goes before everything else.

    ```python
    import clearskies


    class UserPreference(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.SqliteBackend(table_prefix="configuration_")
        id = clearskies.columns.Integer()

        @classmethod
        def destination_name(cls):
            return "preferences"


    cli = clearskies.contexts.Cli(
        clearskies.endpoints.Callable(
            lambda user_preferences: user_preferences.create(no_data=True).id,
        ),
        classes=[UserPreference],
        bindings={
            "global_table_prefix": "user_",
            "sqlite_cursor": clearskies.cursors.SqliteCursor(database_name=":memory:"),
        },
    )
    ```

    """

    supports_n_plus_one = True
    cursor = inject.ByName("sqlite_cursor")
