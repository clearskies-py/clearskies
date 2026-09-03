"""Query parameter pagination adapter for ApiBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from clearskies import configs, decorators
from clearskies.backends.adapters.pagination_adapter import PaginationAdapter

if TYPE_CHECKING:
    from requests import Response as RequestsResponse

    from clearskies.query import Query


class ParameterPaginationAdapter(PaginationAdapter):
    """
    Pagination by incrementing a query parameter (page number or offset).

    Some REST APIs paginate by accepting a query parameter like ``?page=2`` or ``?offset=50``,
    and the client is responsible for incrementing the value to fetch the next page.  This adapter
    handles that pattern by reading the current pagination value from the query and incrementing it
    based on the configured ``step``.

    The adapter determines whether there are more pages by comparing the number of records returned
    against the query's limit.  If the response contains fewer records than the limit, there are no
    more pages.

    ## Page-based pagination

    For APIs that use ``?page=1``, ``?page=2``, etc:

    ```python
    import clearskies

    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        pagination_parameter_name="page",
        pagination_adapter=clearskies.backends.adapters.ParameterPaginationAdapter(
            pagination_parameter_name="page",
            start_value=1,
            step=1,
        ),
    )
    ```

    ## Offset-based pagination

    For APIs that use ``?offset=0``, ``?offset=50``, ``?offset=100``, etc:

    ```python
    import clearskies

    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        pagination_parameter_name="offset",
        pagination_adapter=clearskies.backends.adapters.ParameterPaginationAdapter(
            pagination_parameter_name="offset",
            start_value=0,
            use_limit_as_step=True,
        ),
    )
    ```

    With ``use_limit_as_step=True``, the step size automatically matches the query's limit
    (e.g. if limit is 50, the offset increments by 50 each page).
    """

    """
    The query parameter name the API expects for pagination (e.g. ``"page"``, ``"offset"``, ``"start"``).
    """
    pagination_parameter_name = configs.String(default="page")

    """
    The initial value for the first page (e.g. ``1`` for page-based, ``0`` for offset-based).
    """
    start_value = configs.Integer(default=1)

    """
    The increment for each subsequent page (e.g. ``1`` for page-based).
    Ignored when ``use_limit_as_step`` is ``True``.
    """
    step = configs.Integer(default=1)

    """
    When ``True``, uses the query's ``limit`` as the step size instead of ``step``.
    Typical for offset-based pagination (e.g. offset increments by 50 when limit is 50).
    """
    use_limit_as_step = configs.Boolean(default=False)

    @decorators.parameters_to_properties
    def __init__(
        self,
        pagination_parameter_name: str = "page",
        start_value: int = 1,
        step: int = 1,
        use_limit_as_step: bool = False,
    ):
        """
        Initialize parameter pagination adapter.

        ``pagination_parameter_name`` is the query parameter name the API expects for pagination
        (e.g. ``"page"``, ``"offset"``, ``"start"``).

        ``start_value`` is the initial value for the first page (e.g. ``1`` for page-based, ``0``
        for offset-based).

        ``step`` is the increment for each subsequent page (e.g. ``1`` for page-based).  Ignored
        when ``use_limit_as_step`` is ``True``.

        ``use_limit_as_step`` uses the query's limit as the step size, which is typical for
        offset-based pagination (e.g. offset increments by 50 when limit is 50).
        """
        self.finalize_and_validate_configuration()

    def extract_next_page_data(
        self,
        response: RequestsResponse,
        query: Query,
    ) -> dict[str, Any]:
        """
        Calculate the next page value by incrementing the current pagination parameter.

        Reads the current value from ``query.pagination`` (defaulting to ``start_value`` if not set),
        then increments by ``step`` (or by the query's ``limit`` when ``use_limit_as_step`` is ``True``).

        Returns an empty dict if the response returned fewer records than the limit, indicating
        there are no more pages.
        """
        # Determine step size
        effective_step = self.step
        if self.use_limit_as_step and query.limit:
            effective_step = int(query.limit)

        # Check if there are more pages by comparing response size to limit
        if query.limit and response.content:
            try:
                body = response.json()
                records = body if isinstance(body, list) else body.get("data", body)
                if isinstance(records, list) and len(records) < int(query.limit):
                    return {}
            except Exception:
                pass

        # Get the current value and increment
        current = query.pagination.get(self.pagination_parameter_name, self.start_value)
        try:
            next_value = int(current) + effective_step
        except (ValueError, TypeError):
            return {}

        return {self.pagination_parameter_name: str(next_value)}
