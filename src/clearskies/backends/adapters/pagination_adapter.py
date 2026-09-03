"""Base pagination adapter for ApiBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clearskies.backends.adapters.adapter import Adapter

if TYPE_CHECKING:
    from requests import Response as RequestsResponse

    from clearskies.query import Query


class PaginationAdapter(Adapter["PaginationAdapter"]):
    """
    Base class for pluggable pagination strategies in ``ApiBackend``.

    Responsible for answering one question: **how do I fetch the next page of records?**  This is
    separate from counting (which answers "how many records are there in total?" — see
    :class:`~clearskies.backends.adapters.CountAdapter`).

    Different APIs communicate pagination in completely different ways — some use RFC 5988 Link
    headers, some embed cursors in the response body, some use page numbers or offsets as query
    parameters.  Subclass ``PaginationAdapter`` and override ``extract_next_page_data`` to handle
    your API's pagination style.

    clearskies ships with two concrete implementations:

    - :class:`~clearskies.backends.adapters.LinkHeaderPaginationAdapter` — parses RFC 5988
      ``Link`` headers with ``rel="next"`` (the default for ``ApiBackend``)
    - :class:`~clearskies.backends.adapters.ParameterPaginationAdapter` — reads the next page
      value from a response header or response body field

    ## Implementing a custom adapter

    ```python
    import clearskies


    class CursorPaginationAdapter(clearskies.backends.adapters.PaginationAdapter):
        def extract_next_page_data(self, response, query):
            try:
                data = response.json()
                if cursor := data.get("meta", {}).get("next_cursor"):
                    return {"cursor": cursor}
            except Exception:
                pass
            return {}
    ```

    Attach it to an ``ApiBackend``:

    ```python
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        pagination_adapter=CursorPaginationAdapter(),
    )
    ```

    ## Using a callable

    For simple cases a plain callable may be supplied instead of a full subclass.  The callable
    receives ``(response, query)`` and should return a dictionary with the pagination data needed
    to fetch the next page, or an empty dictionary if there is no next page:

    ```python
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        pagination_adapter=lambda response, query: (
            {"page": response.json()["next_page"]} if response.json().get("next_page") else {}
        ),
    )
    ```
    """

    def extract_next_page_data(
        self,
        response: RequestsResponse,
        query: Query,
    ) -> dict[str, Any]:
        """
        Extract pagination data needed to fetch the next page of records.

        This method has a very important job: it informs clearskies about how to make another API call
        to fetch the next page of records.  It returns a dictionary with whatever pagination information
        is necessary (e.g. a cursor, a page number, an offset).  Returns an empty dict if there is no
        next page.

        Subclasses must override this method.
        """
        return {}
