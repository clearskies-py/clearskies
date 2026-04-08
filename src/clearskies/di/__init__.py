from __future__ import annotations

# Safe to import eagerly: only depend on stdlib. Must be available early
# because clearskies.configs.config imports InjectableProperties as a base class
# before the rest of clearskies has finished initializing.
from clearskies.di.injectable import Injectable
from clearskies.di.injectable_properties import InjectableProperties


def __getattr__(name: str):
    # Lazy-load heavier members (PEP 562) to break the circular import:
    # di/__init__ → AdditionalMygrationsAutoImport/Di → configurable/environment
    # → configs.config → di.__init__ (cycle).
    if name == "inject":
        import clearskies.di.inject as inject

        return inject
    if name == "AdditionalConfig":
        from clearskies.di.additional_config import AdditionalConfig

        return AdditionalConfig
    if name == "AdditionalConfigAutoImport":
        from clearskies.di.additional_config_auto_import import AdditionalConfigAutoImport

        return AdditionalConfigAutoImport
    if name == "AdditionalMygrationsAutoImport":
        from clearskies.di.additional_mygrations_auto_import import AdditionalMygrationsAutoImport

        return AdditionalMygrationsAutoImport
    if name == "Di":
        from clearskies.di.di import Di

        return Di
    raise AttributeError(f"module 'clearskies.di' has no attribute {name!r}")


__all__ = [
    "AdditionalConfig",
    "AdditionalConfigAutoImport",
    "AdditionalMygrationsAutoImport",
    "Di",
    "Injectable",
    "InjectableProperties",
    "inject",
]
