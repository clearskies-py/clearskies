"""ResponseAdapter protocol and default implementation for ApiBackend response extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ResponseAdapter(ABC):
    """
    Pluggable response-extraction strategy for ``ApiBackend``.

    Sits between ``execute_request()`` returning the raw response JSON and the
    ``map_to_model`` pipeline.  Its sole responsibility is answering the
    *structural* question — **where is the data inside the envelope?** — leaving
    the *field-level* question (column name mapping, casing, etc.) to
    ``api_to_model_map`` and ``map_to_model`` as before.

    ## Implementing a custom adapter

    Subclass ``ResponseAdapter`` and override both methods.  Return ``None`` from
    either method to signal "I cannot handle this shape; fall through to the
    built-in ``ApiBackend`` logic":

    ```python
    import clearskies


    class MyServiceResponseAdapter(clearskies.backends.ResponseAdapter):
        def extract_records(self, response_data):
            # unwrap {"results": [...]}
            return response_data.get("results")

        def extract_record(self, response_data):
            # unwrap {"item": {...}}
            return response_data.get("item")
    ```

    Attach it to an ``ApiBackend`` subclass (or directly to an instance):

    ```python
    class MyServiceBackend(clearskies.backends.ApiBackend):
        def __init__(self):
            super().__init__(
                base_url="https://api.example.com",
                response_adapter=MyServiceResponseAdapter(),
            )
    ```

    ## Using a callable

    For simple cases a plain callable may be supplied instead of a full subclass.
    The callable receives the raw response data and should return the extracted
    value, or ``None`` to fall through:

    ```python
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        response_adapter=lambda data: data.get("items"),
    )
    ```

    When a callable is provided it is invoked for **both** ``extract_records`` and
    ``extract_record`` calls.
    """

    @abstractmethod
    def extract_records(self, response_data: Any) -> list[dict[str, Any]] | None:
        """
        Extract a list of raw record dicts from the response envelope.

        Parameters
        ----------
        response_data:
            The parsed JSON body returned by the API.

        Returns
        -------
        list[dict] | None
            The raw list of records, or ``None`` to fall through to the default
            ``ApiBackend`` extraction logic.
        """

    @abstractmethod
    def extract_record(self, response_data: Any) -> dict[str, Any] | None:
        """
        Extract a single raw record dict from the response envelope.

        Parameters
        ----------
        response_data:
            The parsed JSON body returned by the API.

        Returns
        -------
        dict | None
            The raw record dict, or ``None`` to fall through to the default
            ``ApiBackend`` extraction logic.
        """


class DefaultResponseAdapter(ResponseAdapter):
    """
    The default response-extraction strategy used by ``ApiBackend``.

    Encapsulates the extraction heuristics that were previously embedded
    directly in ``map_records_response`` and ``map_record_response``:

    - **Records**: if the response is already a ``list``, return it as-is.
      If it is a ``dict``, return the first ``list`` value found one level
      deep.  Return ``None`` for anything else (e.g. a single-record dict),
      letting ``ApiBackend`` apply its column-aware single-record fallback.
    - **Single record**: always return ``None`` — the existing
      ``check_dict_and_map_to_model`` logic inside ``ApiBackend`` is
      sufficient for the default case and requires column knowledge that the
      adapter does not have.
    """

    def extract_records(self, response_data: Any) -> list[dict[str, Any]] | None:
        """Return the record list from a plain list or a one-level-deep dict wrapper."""
        if isinstance(response_data, list):
            return response_data
        if not isinstance(response_data, dict):
            return None
        for value in response_data.values():
            if isinstance(value, list):
                return value
        return None

    def extract_record(self, response_data: Any) -> dict[str, Any] | None:
        """
        Return ``None`` — delegate to the column-aware ``ApiBackend`` logic.

        Override this in a custom adapter when the API wraps single records in
        an envelope (e.g. ``{"data": {...}}``) that should be unwrapped before
        ``map_to_model`` runs.
        """
        return None
