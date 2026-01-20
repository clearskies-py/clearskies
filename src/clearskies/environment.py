from __future__ import annotations

from typing import Any

from clearskies import configs, configurable, loggable
from clearskies.di import inject, injectable_properties


class Environment(loggable.Loggable, configurable.Configurable, injectable_properties.InjectableProperties):
    """
    This loads up the environment configuration for the application.

    It looks in 3 possible places: first, it looks in os.environ.  Next, it tries to load up the .env file.
    Therefore, the application root directory should be passed in, at will look for a .env file there.
    It should contain lines like NAME=value.  Finally, if there is a value of `secret://path/to/secret`,
    it will use the secret service to look up the secret value.

    It is a very basic parser.  Empty lines and lines starting with a # will be ignored.  Otherwise everything
    is assumed to be a string.
    """

    _env_file_config: dict[str, Any] = {}
    _resolved_values: dict[str, Any] = {}

    secrets = inject.ByName("secrets")
    os = inject.ByStandardLib("os")
    env_file_path = configs.Path(default=".env")
    os_environ = inject.ByStandardLib("os.environ")

    def __init__(self, env_file_path):
        self.env_file_path = env_file_path
        self._resolved_values = {}

    def get(self, name: str, silent: bool = False) -> Any:
        """Get an environment configuration value by name."""
        self.load_env_file()
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
