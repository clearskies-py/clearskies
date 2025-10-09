from __future__ import annotations

import re
from typing import TypeVar

_T = TypeVar("_T")


class Headers(dict[str, str]):
    _duck_cheat = "headers"

    def __init__(self, headers: dict[str, str] = {}) -> None:
        normalized_headers = (
            {key.upper().replace("_", "-"): value for (key, value) in headers.items()} if headers else {}
        )
        super().__init__(normalized_headers)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return super().__contains__(key.upper().replace("_", "-"))

    def __getitem__(self, key: str) -> str:
        return super().__getitem__(key.upper().replace("_", "-"))

    def __setitem__(self, key: str, value: str) -> None:
        if not isinstance(key, str):
            raise TypeError(
                f"Header keys must be strings, but an object of type '{key.__class__.__name__}' was provided."
            )
        if not isinstance(value, str):
            raise TypeError(
                f"Header values must be strings, but an object of type '{value.__class__.__name__}' was provided."
            )
        normalized_key = re.sub("\\s+", " ", key.upper().replace("_", "-"))
        normalized_value = re.sub("\\s+", " ", value.strip())
        super().__setitem__(normalized_key, normalized_value)

    def __getattr__(self, key: str) -> str | None:
        return self.get(key.upper().replace("_", "-"), None)

    def __setattr__(self, key: str, value: str) -> None:
        if key.startswith("_") or key == "_duck_cheat":
            # Allow setting private attributes and special attributes normally
            super().__setattr__(key, value)
        else:
            self.__setitem__(key, value)

    def get(self, key: str, default: _T = None) -> str | _T:  # type: ignore[assignment]
        return super().get(key.upper().replace("_", "-"), default)

    def add(self, key: str, value: str) -> None:
        """Add a header.  This expects a string with a colon separating the key and value."""
        setattr(self, key, value)
