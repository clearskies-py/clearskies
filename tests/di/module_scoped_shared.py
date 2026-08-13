import clearskies


class SharedDependency:
    source = "shared"


class SharedDependencySubclass(SharedDependency):
    source = "shared-subclass"


class GlobalReplacementDependency(SharedDependency):
    source = "global-replacement"


class ModuleScopedBackend:
    source = "module-scoped-backend"


class DefaultBackend:
    source = "default-backend"


class ConfigurableBackend(clearskies.Configurable):
    """A simple Configurable backend for testing config overrides."""

    base_url = clearskies.configs.String(default="https://default.example.com")
    api_version = clearskies.configs.String(default="v1")

    def __init__(self, base_url: str = "https://default.example.com", api_version: str = "v1"):
        self.finalize_and_validate_configuration()
