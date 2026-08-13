from clearskies.di.module_overrides import ModuleOverrides
from tests.di.module_scoped_shared import SharedDependency, SharedDependencySubclass


class ModuleAConfig(ModuleOverrides):
    class_overrides = {
        SharedDependency: SharedDependencySubclass,
    }
    bindings = {
        "module_value": "module-a",
    }
