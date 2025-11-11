from __future__ import annotations

from typing import TYPE_CHECKING

from clearskies.backends import cursor_backend
from clearskies.di import inject

if TYPE_CHECKING:
    pass


class MysqlBackend(cursor_backend.CursorBackend):
    """
    The cursor backend connects your models to a MySQL or MariaDB database.

    ## Installing Dependencies

    clearskies uses PyMySQL to manage the database connection and make queries.  This is not installed by default,
    but is a named extra that you can install when needed via:

    ```bash
    pip install clear-skies[mysql]
    ```

    ## Connecting to your server

    By default, database credentials are expected in environment variables:

    | Name              | Default | Value                                                         |
    |-------------------|---------|---------------------------------------------------------------|
    | DATABASE_HOST     |         | The hostname where the database can be found                  |
    | DATABASE_USERNAME |         | The username to connect as                                    |
    | DATABASE_PASSWORD |         | The password to connect with                                  |
    | DATABASE_NAME     |         | The name of the database to use                               |
    | DATABASE_PORT     | 3306    | The network port to connect to                                |
    | DATABASE_CERT_PATH |         | Path to a certificate to use: enables SSL over the connection |

    However, you can fully control the credential provisioning process by declaring a dependency named `connection_details` and
    setting it to a dictionary with the above keys, minus the `db_` prefix:

    ```python
    class MysqlSettings(clearskies.di.AdditionalConfig):
        provide_mysql_cursor(self, secrets):
            return clearskies.cursors.Mysql(
                host=secrets.get("database_host"),
                username=secrets.get("db_username"),
                password=secrets.get("db_password"),
                database_name=secrets.get("db_database"),
                port=3306,
                cert_path="/path/to/ca",
            )

    wsgi = clearskies.contexts.Wsgi(
        some_application,
        additional_configs=[MysqlSettings()],
        bindings={
            "secrets": "" # some configuration here to point to your secret manager
        }
    )
    ```

    Similarly, some alternate credential provisioning schemes are built into clearskies.  See the
    clearskies.secrets.additional_configs module for those options.

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
     2. The `table_prefix` argument to the CursorBackend constructor adds a prefix of `configuration_`
     3. The `global_table_prefix` binding sets a prefix of `user_`, wihch goes before everything else.

    ```python
    import clearskies


    class UserPreference(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.CursorBackend(table_prefix="configuration_")
        id = clearskies.columns.Uuid()

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
        },
    )
    ```

    """

    supports_n_plus_one = True
    cursor = inject.ByName("mysql_cursor")
