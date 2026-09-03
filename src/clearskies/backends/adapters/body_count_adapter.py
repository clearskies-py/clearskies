"""Response body count adapter for ApiBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clearskies import configs, decorators
from clearskies.backends.adapters.count_adapter import CountAdapter

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

    ## List response

    If the response body is a list, ``count_path`` is ignored and the length of the
    list is used as the total count:

    ```python
    import clearskies

    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        count_adapter=clearskies.backends.adapters.BodyCountAdapter(),
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

    def _resolve_path(self, data: Any, path: str) -> Any:
        """
        Navigate a dot-notation path through a nested dict and return the value.

        Returns ``None`` if any step in the path is missing or the data is not a dict.

        For example, given ``data = {"meta": {"total": 150}}`` and ``path = "meta.total"``,
        this returns ``150``.
        """
        if not path or not isinstance(data, dict):
            return None
        current = data
        for key in path.split("."):
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def extract_count(
        self,
        response_data: Any,
        response_headers: dict[str, str] | None,
        query: Query | None = None,
    ) -> tuple[int | None, int | None]:
        """
        Extract total count and page count from the API response body.

        Navigates the response body using the configured ``count_path`` and ``pages_path``.
        If the response body is a list and no ``count_path`` is set, returns the length of
        the list as the total count.

        Returns ``(None, None)`` if the configured paths cannot be resolved.
        """
        if response_data is None:
            return (None, None)

        total_count = None
        total_pages = None

        if self.count_path:
            value = self._resolve_path(response_data, self.count_path)
            if value is not None:
                try:
                    total_count = int(value)
                except (ValueError, TypeError):
                    pass

        if self.pages_path:
            value = self._resolve_path(response_data, self.pages_path)
            if value is not None:
                try:
                    total_pages = int(value)
                except (ValueError, TypeError):
                    pass

        return (total_count, total_pages)
