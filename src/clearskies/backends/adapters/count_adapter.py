"""Base count adapter for ApiBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clearskies.backends.adapters.adapter import Adapter

if TYPE_CHECKING:
    from clearskies.query import Query


class CountAdapter(Adapter["CountAdapter"]):
    """
    Base class for pluggable count extraction strategies in ``ApiBackend``.

    Responsible for answering one question: **how many records are there in total?**  This is
    separate from pagination (which answers "how do I get the next page?" — see
    :class:`~clearskies.backends.adapters.PaginationAdapter`).

    Different APIs communicate counts in completely different ways — some use response headers,
    some embed counts in the response body, and some don't provide counts at all.  Subclass
    ``CountAdapter`` and override ``extract_count`` to handle your API's counting style.

    clearskies ships with one concrete implementation:

    - :class:`~clearskies.backends.adapters.HeaderCountAdapter` — reads ``X-Total-Count``,
      ``X-Total``, and ``X-Total-Pages`` response headers (the default for ``ApiBackend``)

    ## Implementing a custom adapter

    ```python
    import clearskies


    class BodyCountAdapter(clearskies.backends.adapters.CountAdapter):
        def extract_count(self, response_data, response_headers, query=None):
            if isinstance(response_data, dict):
                total = response_data.get("meta", {}).get("total")
                if total is not None:
                    return (int(total), None)
            return (None, None)
    ```

    Attach it to an ``ApiBackend``:

    ```python
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        count_adapter=BodyCountAdapter(),
    )
    ```

    ## Using a callable

    For simple cases a plain callable may be supplied instead of a full subclass.  The callable
    receives ``(response_headers, response_data)`` and should return a tuple of
    ``(total_count, total_pages)`` where either value can be ``None``:

    ```python
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        count_adapter=lambda headers, data: (
            int(headers["X-My-Total"]) if headers and "X-My-Total" in headers else None,
            None,
        ),
    )
    ```
    """

    def extract_count(
        self,
        response_data: Any,
        response_headers: dict[str, str] | None,
        query: Query | None = None,
    ) -> tuple[int | None, int | None]:
        """
        Extract total count and page count from the API response.

        Returns a tuple of ``(total_count, total_pages)`` where either value can be ``None``
        if the API does not provide that information.

        Subclasses must override this method.
        """
        return (None, None)
