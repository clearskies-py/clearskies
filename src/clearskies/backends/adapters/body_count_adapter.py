"""Response body count adapter for ApiBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clearskies import configs, decorators
from clearskies.backends.adapters.count_adapter import CountAdapter
from clearskies.functional.json import get_nested_attribute

if TYPE_CHECKING:
    from clearskies.query import Query


class BodyCountAdapter(CountAdapter):
    """
    Count extraction from the API response body using a configurable JSON path.

    Some REST APIs return total count information in the response body rather than headers.
    This adapter navigates to a value in the response body using a dot-notation path and
    returns it as the total count.

    ## Simple top-level field

    If your API returns the count at the top level of the response body:

    ```json
    {
        "data": [...],
        "total": 150
    }
    ```

    ```python
    import clearskies

    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        count_adapter=clearskies.backends.adapters.BodyCountAdapter(
            count_path="total",
        ),
    )
    ```

    ## Nested path

    If your API nests the count inside a metadata envelope:

    ```json
    {
        "data": [...],
        "meta": {
            "pagination": {
                "total": 150,
                "pages": 10
            }
        }
    }
    ```

    ```python
    import clearskies

    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        count_adapter=clearskies.backends.adapters.BodyCountAdapter(
            count_path="meta.pagination.total",
            pages_path="meta.pagination.pages",
        ),
    )
    ```
    """

    """
    Dot-notation path to the total count value in the response body
    (e.g. ``"total"``, ``"meta.total"``, ``"meta.pagination.total"``).
    Leave empty to skip count extraction.
    """
    count_path = configs.String(default="")

    """
    Dot-notation path to the total pages value in the response body
    (e.g. ``"pages"``, ``"meta.pages"``).
    Leave empty to skip pages extraction.
    """
    pages_path = configs.String(default="")

    @decorators.parameters_to_properties
    def __init__(
        self,
        count_path: str = "",
        pages_path: str = "",
    ):
        """
        Initialize body count adapter.

        ``count_path`` is a dot-notation path to the total count value in the response body
        (e.g. ``"total"``, ``"meta.total"``, ``"meta.pagination.total"``).  Leave empty to
        skip count extraction from the body.

        ``pages_path`` is a dot-notation path to the total pages value in the response body
        (e.g. ``"pages"``, ``"meta.pages"``).  Leave empty to skip pages extraction.
        """
        self.finalize_and_validate_configuration()

    def extract_count(
        self,
        response_data: Any,
        response_headers: dict[str, str] | None,
        query: Query | None = None,
    ) -> tuple[int | None, int | None]:
        """
        Extract total count and page count from the API response body.

        Navigates the response body using the configured ``count_path`` and ``pages_path``
        via :func:`~clearskies.functional.json.get_nested_attribute`.

        Returns ``(None, None)`` if the configured paths cannot be resolved.
        """
        if response_data is None:
            return (None, None)

        total_count = None
        total_pages = None

        if self.count_path:
            try:
                value = get_nested_attribute(response_data, self.count_path)
                total_count = int(value)
            except (KeyError, ValueError, TypeError):
                pass

        if self.pages_path:
            try:
                value = get_nested_attribute(response_data, self.pages_path)
                total_pages = int(value)
            except (KeyError, ValueError, TypeError):
                pass

        return (total_count, total_pages)
