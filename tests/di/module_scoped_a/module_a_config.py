from clearskies.di.module_overrides import ModuleOverrides
from tests.di.module_scoped_shared import (
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
    bindings = {
        "module_value": "module-a",
    }
