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
