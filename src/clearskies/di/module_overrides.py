from __future__ import annotations

from typing import Any

from clearskies.di.additional_config_auto_import import AdditionalConfigAutoImport


class ModuleOverrides(AdditionalConfigAutoImport):
    """
    Extend this class in a module to declare module-scoped dependency overrides.

    During `Di.add_modules()`, clearskies auto-discovers subclasses of
    `ModuleOverrides` in the imported module tree. Overrides declared here are
    applied only when DI resolves dependencies for classes that originate from
    the same module root.

    Use this to customize a module's dependency graph without changing global
    DI behavior or affecting other modules.

    Resolution priority:

      Type-hinted class injection:
        1. Global class overrides (`Di.add_class_override` / `class_overrides=`)
        2. Module class overrides (`ModuleOverrides.class_overrides`)
        3. `AdditionalConfig.can_build_class()` providers
        4. Built-in predefined classes
        5. Normal class construction

      Name-based injection:
        1. Global bindings (`Di.add_binding` / `bindings=`)
        2. Module bindings (`ModuleOverrides.bindings`)
        3. Classes and by-name class overrides
        4. `AdditionalConfig.provide_*`
        5. Built-ins

    The subclass must not require constructor arguments.

    How to use:

    1) Create a subclass in your module.
    2) Define `class_overrides` and/or `bindings`.
    3) Import that subclass from your module's `__init__.py` so
       `Di.add_modules(your_module)` can discover it.

    Example:
    ```python
    # my_module/module_overrides.py
    from clearskies.backends import ApiBackend
    from clearskies.di import ModuleOverrides
    from my_module.backends import HalJsonApiBackend


    class MyModuleOverrides(ModuleOverrides):
        class_overrides = {
            ApiBackend: HalJsonApiBackend,
        }
        bindings = {
            "api_version": "v2",
            "use_hal": True,
        }
    ```

    ```python
    # my_module/__init__.py
    from .module_overrides import MyModuleOverrides
    from .service import Service

    __all__ = ["MyModuleOverrides", "Service"]
    ```

    ```python
    # my_module/service.py
    from clearskies.backends import ApiBackend


    class Service:
        def __init__(self, api_backend: ApiBackend, api_version: str, use_hal: bool):
            self.api_backend = api_backend
            self.api_version = api_version
            self.use_hal = use_hal
    ```

    ```python
    # app.py
    import my_module
    from clearskies.di import Di

    di = Di(modules=[my_module])
    ```

    In classes from `my_module`, requesting `ApiBackend` by type hint will
    receive `HalJsonApiBackend`, and requesting `api_version` / `use_hal` by
    name will receive `"v2"` / `True`. Other modules are unaffected.
    """

    """
    Class replacements scoped to the declaring module root.

    Keys are the classes to replace; values are the replacement classes or
    objects to use when resolving those types inside this module.
    """
    class_overrides: dict[type, type | Any] = {}

    """
    Name bindings scoped to the declaring module root.

    Keys are DI dependency names; values are the objects or classes to
    provide when those names are requested inside this module.
    """
    bindings: dict[str, Any] = {}

    def get_class_overrides(self) -> dict[type, type | Any]:
        """Return class overrides for this module scope."""
        return self.class_overrides

    def get_bindings(self) -> dict[str, Any]:
        """Return name bindings for this module scope."""
        return self.bindings
