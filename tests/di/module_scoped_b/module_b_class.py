from clearskies.di.injectable_properties import InjectableProperties
from tests.di.module_scoped_shared import DefaultBackend, SharedDependency


class ModuleBClass(InjectableProperties):
    backend = DefaultBackend()

    def __init__(self, shared_dependency: SharedDependency, module_value: str = "module-b-default"):
        self.shared_dependency = shared_dependency
        self.module_value = module_value
