from tests.di.module_scoped_shared import SharedDependency


class ModuleAClass:
    def __init__(self, shared_dependency: SharedDependency, module_value: str):
        self.shared_dependency = shared_dependency
        self.module_value = module_value
