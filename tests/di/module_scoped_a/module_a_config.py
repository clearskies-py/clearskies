from clearskies.di.module_overrides import ModuleOverrides
from tests.di.module_scoped_shared import (
    ConfigurableBackend,
    DefaultBackend,
    ModuleScopedBackend,
    SharedDependency,
    SharedDependencySubclass,
)


class ModuleAConfig(ModuleOverrides):
    class_overrides = {
        SharedDependency: SharedDependencySubclass,
        DefaultBackend: ModuleScopedBackend,
    }
    config_overrides = {
        ConfigurableBackend: {"base_url": "https://module-a.example.com", "api_version": "v2"},
    }
    bindings = {
        "module_value": "module-a",
    }
