from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from clearskies import configurable

if TYPE_CHECKING:
    import clearskies.column
    import clearskies.model


class Validator(ABC, configurable.Configurable):
    """
    Attach input validation rules to columns!

    The validators provide a way to attach input validation logic to columns.  The columns themselves already
    provide basic validation (making sure strings are strings, integers are integers, etc...) but these classes
    allow for more detailed rules.

    It's important to understand that validators only apply to client input, which means that input validation
    is only enforced by appropriate endpoints.  If you inject a model into a function of your own and execute
    a save operation with it, validators will **NOT** be checked.
    """

    is_unique = False
    is_required = False

    def __call__(self, model: clearskies.model.Model, column_name: str, data: dict[str, Any]) -> str:
        return self.check(model, column_name, data)

    @abstractmethod
    def check(self, model: clearskies.model.Model, column_name: str, data: dict[str, Any]) -> str:
        pass

    def additional_write_columns(self, is_create=False) -> dict[str, clearskies.column.Column]:
        return {}
