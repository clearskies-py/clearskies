"""ResponseAdapter base implementation for ApiBackend response extraction."""

from __future__ import annotations

from typing import Any


class ResponseAdapter:
    """
    Pluggable response-extraction strategy for ``ApiBackend``.

    Sits between ``execute_request()`` returning the raw response JSON and the
    ``map_to_model`` pipeline.  Its sole responsibility is answering the
    *structural* question — **where is the data inside the envelope?** — leaving
    the *field-level* question (column name mapping, casing, etc.) to
    ``api_to_model_map`` and ``map_to_model`` as before.

    ## Implementing a custom adapter

    Subclass ``ResponseAdapter`` and override either/both methods.  Return ``None`` from
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

        Default behavior:
        - If ``response_data`` is a ``list``, return it as-is.
        - If ``response_data`` is a ``dict``, return the first one-level-deep ``list`` value.
        - Otherwise return ``None``.
        """
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

        Default behavior:
        - Return ``None`` and delegate to the column-aware ``ApiBackend`` logic.
        """
        return None
