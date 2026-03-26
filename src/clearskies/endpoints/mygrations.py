from __future__ import annotations

from typing import TYPE_CHECKING

from clearskies import configs, decorators
from clearskies.endpoint import Endpoint
from clearskies.exceptions import ClientError, InputErrors

if TYPE_CHECKING:
    from clearskies.cursors import Cursor
    from clearskies.input_outputs import InputOutput


class Mygrations(Endpoint):
    """
    An endpoint to run database migrations via the mygrations library.

    You must install mygrations separately to use this endpoint:

    ```
    pip install mygrations
    ```

    See the rep for mygrations documentation:

    [https://github.com/cmancone/mygrations](https://github.com/cmancone/mygrations)

    Mygrations is a stateless database migration system.  You define your desired database schema
    via SQL (using `CREATE TABLE` commands) and point mygrations at both your SQL files and your
    database.  It will then compare the two and calculate what changes need to be made to bring
    your database in line with your files.  Like most IaC, mygrations then relies on your standard
    plan/apply combination.  Here's a simple example:

    ```
    import clearskies

    cli = clearskies.contexts.Cli(
        clearskies.endpoints.Mygrations(
            allow_input=True,
            cursor=clearskies.cursors.from_environment.Mysql(),
            sql=["./database/"],
        )
    )
    cli()
    ```

    This would find database connection details in your environment and would look for `*.sql` files
    in the `database` folder.  You could then call this script to plan/apply/whatever:

    ```
    ./mygrate.py --command=plan
    ./mygrate.py --command=apply
    ```

    **Auto-imported migration paths**

    If any module that was imported into the Di container via `add_modules()` contains a class that
    extends `clearskies.di.AdditionalMygrationsAutoImport`, the SQL paths declared by that class
    will automatically be prepended to the `sql` list before migrations run.

    The endpoint's explicit `sql` configuration takes deduplication priority: if an auto-imported
    path matches one already declared in `sql`, only the endpoint's copy is used (at the end of
    the final list).  Non-existent paths from auto-imported configs are silently skipped.

    Discovery order is preserved; paths from modules discovered earlier appear first.
    """

    """
    Whether or not to allow the mygrations endpoint to accept input for its configuration

    To run, the migrations endpoint needs to know which mygration command to use and where
    the SQL files live.  These can be set exclusively via the endpoint configuration, or
    (if this flag is set to true) they can be set via request parameters through whatever
    context the endpoint is attached to.
    """
    allow_input = configs.Boolean(default=False)

    """
    The mygrations command to execute

    See https://github.com/cmancone/mygrations#command-line-usage for the relevant docs.  Current allowed commands are:

     * `version`
     * `check`
     * `plan`
     * `plan_export`
     * `apply`
    """
    command = configs.Select(["version", "check", "plan", "plan_export", "apply"], default="version")

    """
    The SQL to use as a source of truth.

    This is a list of strings, and each string value can be one of the following:

     1. A valid SQL string.
     2. A path to a file containing SQL.
     3. A path to a directory containing SQL files.

    The combination of all SQL you pass in (either directly or by referencing files/directories) becomes the
    source of truth that mygrations will attempt to bring your database to.

    In addition, any paths declared via `AdditionalMygrationsAutoImport` subclasses found in modules
    imported into the Di container are automatically prepended to this list (deduplicated, with this
    explicit list taking dedup priority).
    """
    sql = configs.StringList(default=["./database"])

    """
    The dependency name to fetch the cursor from.

    If you set both this and `cursor`, then `cursor` takes precedence.
    """
    cursor_dependency_name = configs.String(default="cursor")

    """
    Whether to include auto-imported module migrations.

    If true, the endpoint will include SQL paths from any `AdditionalMygrationsAutoImport`
    subclasses discovered by the Di container.  If false (the default), auto-imported
    module migrations are ignored entirely.
    """
    include_module_migrations = configs.Boolean(default=False)

    """
    Optional allow-list of `AdditionalMygrationsAutoImport` subclass names to include.

    When `include_module_migrations` is true and this list is **empty** (the default),
    *all* discovered subclasses contribute their SQL paths.  When this list is **non-empty**,
    only subclasses whose class name appears in the list are included.

    The entries must be the **class name** (e.g. `"GitlabMetadataMigrations"`), not the
    module path.

    Example:
    ```python
    clearskies.endpoints.Mygrations(
        include_module_migrations=True,
        module_migrations=["GitlabMetadataMigrations", "AuditLogMigrations"],
    )
    ```
    """
    module_migrations = configs.StringList(default=[])

    _cursor: Cursor

    @decorators.parameters_to_properties
    def __init__(
        self,
        cursor_dependency_name: str = "cursor",
        allow_input: bool = False,
        command: str = "version",
        sql: list[str] | None = None,
        include_module_migrations: bool = False,
        module_migrations: list[str] = [],
        url: str = "",
    ):
        # we need to call the parent but don't have to pass along any of our kwargs.  They are all optional in our parent, and our parent class
        # just stores them in parameters, which we have already done.  However, the parent does do some extra initialization stuff that we need,
        # which is why we have to call the parent.
        super().__init__()

    @property
    def cursor(self) -> Cursor:
        """
        Lazily inject and return the database cursor instance.

        Returns
        -------
            The cursor object used for executing database queries.
        """
        if not hasattr(self, "_cursor"):
            self._cursor = self.di.build(self.cursor_dependency_name)
        return self._cursor

    def handle(self, input_output: InputOutput):
        try:
            from mygrations.core.commands import execute  # type: ignore
        except ModuleNotFoundError as e:
            raise ValueError("mygrations is not installed.")

        self.di.inject_properties(self.cursor.__class__)

        command_config = getattr(self.__class__, "command")
        command = self._from_input_or_config("command", input_output)
        if command not in command_config.allowed_values:
            raise InputErrors(
                {
                    "command": f"Invalid command: I received '{command}' but it must be one of "
                    + ", ".join(command_config.allowed_values)
                }
            )

        # Collect auto-imported mygration paths (prepend), deduplicated.
        # The endpoint's explicit sql list has dedup priority: seed the seen-set with it first
        # so any auto-imported path that duplicates an explicit one is silently dropped.
        # When module_migrations is non-empty, only those specific classes contribute paths.
        auto_paths = (
            self.di.get_mygrations_sql_paths(self.module_migrations or None) if self.include_module_migrations else []
        )
        seen: set[str] = set(self.sql)
        merged_sql: list[str] = []
        for path in auto_paths:
            if path not in seen:
                seen.add(path)
                merged_sql.append(path)
        merged_sql.extend(self.sql)

        # Mygrations requires autocommit to be disabled. Store previous state and restore after.
        previous_autocommit = self.cursor.autocommit
        self.cursor.set_autocommit(False)
        try:
            [output, success] = execute(
                command, {"connection": self.cursor.connection, "sql_files": merged_sql}, print_results=False
            )
        finally:
            self.cursor.set_autocommit(previous_autocommit)

        if not success:
            raise ClientError("\n".join(output))
        return self.success(input_output, output)

    def _from_input_or_config(self, key, input_output):
        if self.allow_input:
            if input_output.request_data is not None and key in input_output.request_data:
                return input_output.request_data[key]
        return getattr(self, key)
