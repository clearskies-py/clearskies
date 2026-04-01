import tempfile

from clearskies.di import AdditionalMygrationsAutoImport


class MigrationsWithDefaultSql(AdditionalMygrationsAutoImport):
    """Uses the default sql_dir = ["sql"] resolved relative to this file."""

    pass


# Points at a real tmpdir created at import-time so we can assert
# that Di.add_modules() discovers and returns it.
_custom_sql_dir = tempfile.mkdtemp()


class MigrationsWithCustomSql(AdditionalMygrationsAutoImport):
    def __init__(self):
        super().__init__(sql_dir=[_custom_sql_dir])


__all__ = [
    "MigrationsWithDefaultSql",
    "MigrationsWithCustomSql",
    "_custom_sql_dir",
]
