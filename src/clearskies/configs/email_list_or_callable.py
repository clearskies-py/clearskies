from __future__ import annotations

from clearskies.configs import string_list_or_callable


class EmailListOrCallable(string_list_or_callable.StringListOrCallable):
    """
    This is for a configuration that should be a list of emails or a callable that returns a list of emails.

    This is different than StringList, which also accepts a list of strings, but
    validates that all of those values match the email format.
    """

    def __init__(
        self, required=False, default=None, regexp: str = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    ):
        super().__init__(required=required, default=default, regexp=regexp)
