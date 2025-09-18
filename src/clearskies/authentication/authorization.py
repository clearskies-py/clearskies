from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clearskies.input_outputs.input_output import InputOutput
    from clearskies.model import Model


class Authorization:
    """Authorization."""

    def gate(self, authorization_data, input_output: InputOutput) -> bool:
        """
        Return True/False to denote if the given user, as represented by the authorization data, should be allowed access.

        Raise clearskies.exceptions.ClientError if you want to raise a specific error message.
        """
        return True

    def filter_model(self, model: Model, authorization_data, input_output: InputOutput) -> Model:
        """Return a models object with additional filters applied to account for authorization needs."""
        return model
