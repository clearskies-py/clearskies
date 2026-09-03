"""Generic base class for all adapter types."""

from __future__ import annotations

from typing import Generic, TypeVar

from clearskies.configurable import Configurable

AdapterType = TypeVar("AdapterType")


class Adapter(Configurable, Generic[AdapterType]):
    """
    Base class for pluggable adapters.

    Extends :class:`~clearskies.configurable.Configurable` so that all adapters
    support clearskies config descriptors, the ``@parameters_to_properties``
    decorator, and ``finalize_and_validate_configuration()``.

    Subclasses define the adapter protocol by implementing the required methods.

    Usage::

        class MyUrlAdapter(UrlAdapter):
            # Override methods to customise URL generation
            pass
    """
