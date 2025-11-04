from abc import ABC
from typing import Any, Self

from clearskies import configurable
from clearskies.configs import boolean, string
from clearskies.decorators import parameters_to_properties
from clearskies.di import inject, injectable_properties


class Base(ABC, configurable.Configurable, injectable_properties.InjectableProperties):
    """Abstract base class for database cursors."""

    cursor_type: str
    environment = inject.Environment()
    database_name = string.String(default=None)
    autocommit = boolean.Boolean(default=True)

    @parameters_to_properties
    def __init__(self, database_name: str | None = None, autocommit: bool | None = None):
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
        super().finalize_and_validate_configuration()

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

    def __call__(self) -> Self:
        """Return the cursor instance."""
        with self.connection as conn:
            cursor = conn.cursor()
            return cursor
