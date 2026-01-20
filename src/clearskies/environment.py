from __future__ import annotations

from typing import Any

from clearskies import configs, configurable, loggable
from clearskies.di import inject, injectable_properties


class Environment(loggable.Loggable, configurable.Configurable, injectable_properties.InjectableProperties):
    """
    Load and manage environment configuration for the application.

    The Environment class provides a unified interface for accessing configuration values from multiple sources.
    It looks in 4 possible places (in order of priority):

    1. Values set programmatically via the `set()` method
    2. Values from `os.environ`
    3. Values from a `.env` file
    4. Secret values referenced via `secret://path/to/secret`

    The `.env` file should contain lines like `NAME=value`. Empty lines and lines starting with `#` are ignored.
    Values are automatically parsed into appropriate Python types (bool, int, float, or string).

    Example usage:

    ```python
    import clearskies


    # The environment is typically accessed via dependency injection
    def my_function(environment: clearskies.Environment):
        # Get a value (raises KeyError if not found)
        database_url = environment.get("DATABASE_URL")

        # Get a value silently (returns None if not found)
        optional_value = environment.get("OPTIONAL_KEY", silent=True)

        # Set a value programmatically (highest priority)
        environment.set("MY_OVERRIDE", "custom_value")


    # Or access it directly from the DI container
    di = clearskies.di.Di()
    environment = di.build("environment")
    ```

    Example `.env` file:

    ```
    # Database configuration
    DATABASE_URL=postgresql://localhost/mydb
    DEBUG=true
    MAX_CONNECTIONS=10
    TIMEOUT=30.5

    # Secret reference (will be fetched from secret engine)
    API_KEY=secret:///my/api/key
    ```
    """

    _env_file_config: dict[str, Any] = {}
    _resolved_values: dict[str, Any] = {}
    _overrides: dict[str, Any] = {}

    """
    The secrets engine used to resolve `secret://` references.

    When a configuration value starts with `secret://`, the Environment class will use this
    secrets engine to fetch the actual value. This is injected via dependency injection.
    """
    secrets = inject.ByName("secrets")

    """
    The os module, injected for accessing file system operations.
    """
    os = inject.ByStandardLib("os")

    """
    The path to the `.env` file.

    Defaults to `.env` in the current working directory. This can be overridden
    when constructing the Environment instance.
    """
    env_file_path = configs.Path(default=".env")

    """
    The os.environ dictionary, injected for accessing environment variables.

    This is injected via dependency injection to allow for easier testing and mocking.
    """
    os_environ = inject.ByStandardLib("os.environ")

    def __init__(self, env_file_path):
        self.env_file_path = env_file_path
        self._resolved_values = {}
        self._overrides = {}

    def set(self, name: str, value: Any) -> None:
        """
        Set an environment configuration value programmatically.

        Values set via this method take the highest priority and will override values from
        `os.environ` and the `.env` file. This is useful for testing or for setting values
        that need to be computed at runtime.

        The value can be any type, including a `secret://` reference which will be resolved
        when retrieved via `get()`.

        ```python
        import clearskies


        def configure_environment(environment: clearskies.Environment):
            # Set a simple value
            environment.set("API_URL", "https://api.example.com")

            # Set a computed value
            environment.set("CACHE_SIZE", calculate_optimal_cache_size())

            # Set a secret reference (will be resolved on get())
            environment.set("API_KEY", "secret:///production/api/key")

            # Override an existing environment variable
            environment.set("DEBUG", False)  # Even if DEBUG=true in .env
        ```
        """
        self._overrides[name] = value

    def get(self, name: str, silent: bool = False) -> Any:
        """
        Get an environment configuration value by name.

        Retrieves a configuration value by checking sources in the following priority order:

        1. Values set via `set()` (highest priority)
        2. Values from `os.environ`
        3. Values from the `.env` file (lowest priority)

        If the value starts with `secret://`, it will be resolved using the configured
        secrets engine before being returned. If the key is not found and `silent` is False,
        a KeyError will be raised. If `silent` is True, None will be returned instead.

        ```python
        import clearskies


        def my_function(environment: clearskies.Environment):
            # Get a required value (raises KeyError if not found)
            database_url = environment.get("DATABASE_URL")

            # Get an optional value (returns None if not found)
            debug_mode = environment.get("DEBUG", silent=True)
            if debug_mode is None:
                debug_mode = False

            # Values are automatically typed
            max_connections = environment.get("MAX_CONNECTIONS")  # Returns int
            timeout = environment.get("TIMEOUT")  # Returns float
            enabled = environment.get("ENABLED")  # Returns bool for "true"/"false"
        ```
        """
        self.load_env_file()
        if name in self._overrides:
            return self.resolve_value(self._overrides[name])
        if name in self.os_environ:
            return self.resolve_value(self.os_environ[name])
        if name in self._env_file_config:
            return self.resolve_value(self._env_file_config[name])

        if not silent:
            raise KeyError(f"Could not find environment config '{name}' in environment or .env file")
        return None

    def load_env_file(self):
        """Load up the .env file if it has not already been loaded."""
        if self._env_file_config is not None:
            return

        self._env_file_config = {}

        with open(self.env_file_path, "r") as env_file:
            line_number = 0
            for line in env_file.readlines():
                line_number += 1
                key, value = self._parse_env_line(line, line_number)
                if key is None:
                    continue

                self._env_file_config[key] = value

    def _parse_env_line(self, line: str, line_number: int) -> tuple[str | None, Any]:
        line = line.strip()
        if not line:
            return (None, None)
        if line[0] == "#":
            return (None, None)
        if not "=" in line:
            raise ValueError(f"Parse error in environment line #{line_number}: should be 'key=value'")

        equal_index = line.index("=")
        key = line[:equal_index].strip()
        value = line[equal_index + 1 :].strip()
        lc_value = value.lower()
        if lc_value == "true":
            return (key, True)
        if lc_value == "false":
            return (key, False)
        if lc_value[0] == '"' and lc_value[-1] == '"':
            return (key, value.strip('"'))
        if lc_value[0] == "'" and lc_value[-1] == "'":
            return (key, value.strip("'"))
        try:
            as_int = int(value)
            return (key, as_int)
        except:
            pass
        try:
            as_float = float(value)
            return (key, as_float)
        except:
            pass
        return (key, value)

    def resolve_value(self, value: str | Any) -> Any:
        """Resolve a value, looking up secrets as needed."""
        if type(value) != str or value[:9] != "secret://":
            return value

        secret_path = value[9:]
        if secret_path[0] != "/":
            secret_path = f"/{secret_path}"
        if secret_path not in self._resolved_values:
            if not self.secrets:
                raise ValueError(
                    "References to the secret engine were found in the environment, "
                    + "but a secret engine was not provided"
                )
            self._resolved_values[secret_path] = self.secrets.get(secret_path)
        return self._resolved_values[secret_path]
