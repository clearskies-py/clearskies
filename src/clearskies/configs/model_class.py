from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Self, overload

from clearskies.configs import config
from clearskies.functional import validations

if TYPE_CHECKING:
    from clearskies.model import Model, ModelClassReference


class ModelClass(config.Config):
    """A config that accepts a model class."""

    def __set__(self, instance, value: type[Model | ModelClassReference]):
        try:
            validations.is_model_class_or_reference(value, raise_error_message=True, strict=False)
        except TypeError as e:
            error_prefix = self._error_prefix(instance)
            raise TypeError(f"{error_prefix} {str(e)}")

        # reference or model class?
        instance._set_config(self, value)

    @overload
    def __get__(self, instance: None, parent: type) -> Self: ...
    @overload
    def __get__(self, instance: object, parent: type) -> type[Model]: ...
    def __get__(self, instance, parent):
        if not instance:
            return self

        value = instance._get_config(self)
        if validations.is_model_class_reference(value):
            class_reference = value() if inspect.isclass(value) else value
            instance._set_config(self, class_reference.get_model_class())

        return instance._get_config(self)
