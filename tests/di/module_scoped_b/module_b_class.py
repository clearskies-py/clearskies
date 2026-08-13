from clearskies.di.injectable_properties import InjectableProperties
from tests.di.module_scoped_shared import ConfigurableBackend, DefaultBackend, SharedDependency


class ModuleBClass(InjectableProperties):
    backend = DefaultBackend()
    configurable_backend = ConfigurableBackend()

    def __init__(self, shared_dependency: SharedDependency, module_value: str = "module-b-default"):
        self.shared_dependency = shared_dependency
        self.module_value = module_value
