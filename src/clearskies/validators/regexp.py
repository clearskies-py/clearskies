from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from clearskies import configs
from clearskies.validator import Validator

if TYPE_CHECKING:
    from clearskies import Model


class Regexp(Validator):
    r"""
    Validates that a column value matches the given regular expression.

    Example:
    ```
    import clearskies


    class MyModel(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()

        id = clearskies.columns.Uuid()
        version = clearskies.columns.String(validators=[clearskies.validators.Regexp(r"\d+\.\d+\.\d+")])
    ```
    """

    """
    The regular expression that input must match.
    """
    regexp = configs.String(required=True)

    """
    Whether or not to include the regular expression in the error message, if the input doesn't match.
    """
    include_regexp_in_error = configs.Boolean(default=False)

    _re_compiled: re.Pattern

    def __init__(self, regexp: str, include_regexp_in_error: bool = False):
        self.regexp = regexp
        self.include_regexp_in_error = include_regexp_in_error
        self.finalize_and_validate_configuration()

    def check(self, model: Model, column_name: str, data: dict[str, Any]) -> str:
        # we won't check anything for missing values (columns should be required if that is an issue)
        if not data.get(column_name):
            return ""
        if not hasattr(self, "_re_compiled"):
            self._re_compiled = re.compile(self.regexp)
        if self._re_compiled.match(data[column_name]):
            return ""

        suffix = f", '{self.regexp}'." if self.include_regexp_in_error else "."
        return f"Does not match the required pattern{suffix}"
