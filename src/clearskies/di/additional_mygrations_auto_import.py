from __future__ import annotations

import sys
from pathlib import Path

from clearskies import configs
from clearskies.configurable import Configurable
from clearskies.decorators import parameters_to_properties


class AdditionalMygrationsAutoImport(Configurable):
    """
    Extend this class in any module that ships SQL database migrations.

    The Di container will auto-discover subclasses during add_modules() and
    register the sql paths returned by sql_paths(). The Mygrations endpoint
    will automatically prepend those paths (deduplicated, with the endpoint's
    explicit sql list taking dedup priority) before executing migrations.

    By default, `sql` points to a folder named `sql` next to the module file
    that defines the subclass.  Override `sql` to point elsewhere — relative
    paths are resolved relative to the defining module's file, absolute paths
    are passed through unchanged.  Non-existent paths are silently skipped.

    The subclass must not require constructor arguments.

    Example (zero boilerplate — default sql folder named `sql`):

    ```python
    # my_module/migrations.py
    from clearskies.di import AdditionalMygrationsAutoImport


    class MyModuleMigrations(AdditionalMygrationsAutoImport):
        pass


    # my_module/__init__.py
    from .migrations import MyModuleMigrations  # just needs to be imported
    ```

    Example (custom folder names):

    ```python
    class MyModuleMigrations(AdditionalMygrationsAutoImport):
        sql = ["database", "schema"]  # both resolved relative to this module's file
    ```
    """

    """
    The base directory to resolve relative SQL paths against.
    By default, this is the directory of the module that defines the concrete subclass.
    Override `base_dir` to change this behavior.
    """
    base_dir = configs.Path(default=None)

    """
    The list of SQL file paths or directories this module contributes, as strings.
    Relative paths are resolved relative to the module file that defines the concrete subclass.
    Non-existent paths are silently skipped.
    """
    sql_dir = configs.PathList(default=["sql"])

    @parameters_to_properties
    def __init__(self, base_dir: Path | None = None, sql_dir: list[str | Path] = ["sql"]):
        self.finalize_and_validate_configuration()

    def get_base_dir(self) -> Path:
        """
        Get the base directory to resolve relative SQL paths against.

        By default, this is the directory of the module that defines the concrete subclass.
        Override `base_dir` to change this behavior.
        """
        if self.base_dir is not None:
            return self.base_dir
        module_file = sys.modules[self.__class__.__module__].__file__
        return Path(module_file).parent if module_file else Path(".")

    def sql_paths(self) -> list[str]:
        """
        Return resolved, existing SQL paths this module contributes as strings.

        Relative entries in sql are resolved relative to the module file that
        defines the concrete subclass before the existence check runs.  Non-existent
        paths are silently omitted.
        """
        base_dir = self.get_base_dir()

        # Determine the raw sql entries to iterate over.
        # Priority: instance _config dict (set via descriptor __set__), then the class
        # attribute which may be either a PathList descriptor (use its default) or a
        # plain list override declared directly on a subclass.
        if self._config and "sql_dir" in self._config:
            raw_entries: list[str | Path] = self._config["sql_dir"]
        else:
            class_attr = self.__class__.__dict__.get("sql_dir", None)
            if isinstance(class_attr, list):
                # Subclass declared `sql_dir = [...]` directly — use it as-is.
                raw_entries = class_attr
            else:
                # Fall back to the PathList descriptor default on the base class.
                raw_entries = ["sql"]

        result: list[str] = []
        for entry in raw_entries:
            path = Path(entry)
            if not path.is_absolute():
                path = base_dir / path
            if path.exists():
                result.append(str(path))
        return result
