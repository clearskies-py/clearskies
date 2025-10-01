from __future__ import annotations

from clearskies.configs import string


class Email(string.String):
    def __init__(
        self, required=False, default=None, regexp: str = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    ):
        super().__init__(required=required, default=default, regexp=regexp)
