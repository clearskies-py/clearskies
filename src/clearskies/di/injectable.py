from abc import ABC, abstractmethod
from typing import Any


class Injectable(ABC):
    _di: Any = None

    def initiated_guard(self, instance):
        if self._di:
            return

        reference = instance.__class__.__name__ + "."
        my_id = id(self)
        cls = instance.__class__
        for attribute_name in dir(instance):
            if id(getattr(cls, attribute_name)) != my_id:
                continue
            reference += attribute_name
        raise ValueError(
            f"There was an attempt to get a value out of '{reference}' but the injectable hasn't been properly "
            + "initialized.  This usually means that objects are being created outside of the normal Di system. "
            + "This most often happens when working with classes that are both configurable and have injectables: "
            + "in this case, your class can't make use of any injectables in the __init__ function, as the injectables "
            + "will only be provided later.  Any use of injectables must be deferred until after object creation."
        )

    def set_di(self, di):
        self._di = di

    @abstractmethod
    def __get__(self, instance, parent):
        pass
