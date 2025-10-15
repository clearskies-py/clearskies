from __future__ import annotations

from abc import ABC
from typing import Any

import clearskies.configurable
from clearskies.di.injectable_properties import InjectableProperties


class Secrets(ABC, clearskies.configurable.Configurable, InjectableProperties):
    def create(self, path: str, value: str) -> bool:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def get(self, path: str, silent_if_not_found: bool = False) -> str:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def list_secrets(self, path: str) -> list[Any]:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def update(self, path: str, value: Any) -> None:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def upsert(self, path: str, value: Any) -> None:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )

    def list_sub_folders(self, path: str) -> list[Any]:
        raise NotImplementedError(
            "It looks like you tried to use the secret system in clearskies, but didn't specify a secret manager."
        )
