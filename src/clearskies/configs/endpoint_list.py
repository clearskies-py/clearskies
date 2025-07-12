from __future__ import annotations

from typing import TYPE_CHECKING

from clearskies.configs import config

if TYPE_CHECKING:
    from clearskies.endpoint import Endpoint as EndpointBase


class EndpointList(config.Config):
    def __set__(self, instance, value: list[EndpointBase]):
        if not isinstance(value, list):
            raise TypeError(
                f"{error_prefix} attempt to set a value of type '{value.__class__.__name__}' to a parameter that requries a list of endpoints."
            )
        for index, item in enumerate(value):
            if not hasattr(item, "top_level_authentication_and_authorization"):
                error_prefix = self._error_prefix(instance)
                raise TypeError(
                    f"{error_prefix} attempt to set a value of type '{item.__class__.__name__}' for item #{index+1} when all items in the list should be instances of clearskies.End."
                )
        instance._set_config(self, value)

    def __get__(self, instance, parent) -> list[EndpointBase]:
        if not instance:
            return self  # type: ignore
        return instance._get_config(self)
