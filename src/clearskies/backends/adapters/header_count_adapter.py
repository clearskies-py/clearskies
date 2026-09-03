"""Response header count adapter for ApiBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clearskies.backends.adapters.count_adapter import CountAdapter

if TYPE_CHECKING:
    from clearskies.query import Query


class HeaderCountAdapter(CountAdapter):
    """
    Count extraction from HTTP response headers.

    Many REST APIs communicate total record counts via response headers.  This adapter reads
    common count headers (case-insensitive) and returns the extracted values.

    This is the default count adapter used by ``ApiBackend``.

    ## Supported headers

    - ``X-Total-Count`` or ``X-Total`` — total number of records matching the query
    - ``X-Total-Pages`` — total number of pages

    ## Usage

    ```python
    import clearskies

    # Explicit usage (this is also the default when no count_adapter is provided):
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        count_adapter=clearskies.backends.adapters.HeaderCountAdapter(),
    )
    ```

    ## Custom header names

    If your API uses different header names, subclass and override ``extract_count``:

    ```python
    class MyCountAdapter(clearskies.backends.adapters.HeaderCountAdapter):
        def extract_count(self, response_data, response_headers, query=None):
            if not response_headers:
                return (None, None)
            total = response_headers.get("X-My-Api-Total")
            pages = response_headers.get("X-My-Api-Pages")
            if total is not None:
                return (int(total), int(pages) if pages else None)
            return (None, None)
    ```
    """

    def extract_count(
        self,
        response_data: Any,
        response_headers: dict[str, str] | None,
        query: Query | None = None,
    ) -> tuple[int | None, int | None]:
        """
        Extract total count and page count from HTTP response headers.

        Returns a tuple of ``(total_count, total_pages)`` where either value can be ``None``
        if the API does not provide that information.  Header matching is case-insensitive.

        Default behavior:
        - Reads ``X-Total-Count`` or ``X-Total`` headers for total record count.
        - Reads ``X-Total-Pages`` header for total page count.
        - Returns ``(None, None)`` if no recognized headers are present.
        """
        if not response_headers:
            return (None, None)

        headers_lower = {k.lower(): v for k, v in response_headers.items()}

        total_count = None
        total_pages = None

        if "x-total-count" in headers_lower:
            try:
                total_count = int(headers_lower["x-total-count"])
            except (ValueError, TypeError):
                pass
        elif "x-total" in headers_lower:
            try:
                total_count = int(headers_lower["x-total"])
            except (ValueError, TypeError):
                pass

        if "x-total-pages" in headers_lower:
            try:
                total_pages = int(headers_lower["x-total-pages"])
            except (ValueError, TypeError):
                pass

        return (total_count, total_pages)
