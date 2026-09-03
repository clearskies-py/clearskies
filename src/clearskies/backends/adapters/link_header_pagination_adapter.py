"""RFC 5988 Link header pagination adapter for ApiBackend."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any

from clearskies import configs, decorators
from clearskies.backends.adapters.pagination_adapter import PaginationAdapter

if TYPE_CHECKING:
    from requests import Response as RequestsResponse

    from clearskies.query import Query


class LinkHeaderPaginationAdapter(PaginationAdapter):
    """
    Pagination via RFC 5988 ``Link`` headers.

    Many REST APIs use the ``Link`` header to communicate pagination, following the standard
    defined in `RFC 5988 <https://tools.ietf.org/html/rfc5988>`_.  The server includes a
    ``Link`` header with ``rel="next"`` pointing to the URL for the next page:

    ```
    Link: <https://api.example.com/users?start=50>; rel="next"
    ```

    This adapter parses that header and extracts the configured ``pagination_parameter_name``
    from the next link's query string to build the pagination data for the next request.

    This is the default pagination adapter used by ``ApiBackend``.

    ## Usage

    ```python
    import clearskies

    # Explicit usage (this is also the default when no pagination_adapter is provided):
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        pagination_adapter=clearskies.backends.adapters.LinkHeaderPaginationAdapter(
            pagination_parameter_name="page",
        ),
    )
    ```

    ## How it works

    Given a response with this header:

    ```
    Link: <https://api.example.com/users?page=3>; rel="next", <https://api.example.com/users?page=1>; rel="prev"
    ```

    And ``pagination_parameter_name="page"``, this adapter returns ``{"page": "3"}``.  That dictionary
    is then passed back into the next API request as pagination data.
    """

    """
    The query parameter name to extract from the ``rel="next"`` link URL
    (e.g. ``"page"``, ``"start"``, ``"since"``, ``"cursor"``).
    """
    pagination_parameter_name = configs.String(default="start")

    @decorators.parameters_to_properties
    def __init__(self, pagination_parameter_name: str = "start"):
        """
        Initialize Link header pagination adapter.

        ``pagination_parameter_name`` is the query parameter name to extract from the ``rel="next"``
        link URL (e.g. ``"page"``, ``"start"``, ``"since"``, ``"cursor"``).
        """
        self.finalize_and_validate_configuration()

    def extract_next_page_data(
        self,
        response: RequestsResponse,
        query: Query,
    ) -> dict[str, Any]:
        """
        Extract next-page data from the RFC 5988 ``Link`` header.

        Parses the ``Link`` header for a link with ``rel="next"``, then extracts the configured
        ``pagination_parameter_name`` from the link's query string.

        For example, given:

        ```
        Link: <https://api.example.com/users?start=50>; rel="next"
        ```

        And ``pagination_parameter_name="start"``, this returns ``{"start": "50"}``.

        Returns an empty dict if there is no ``Link`` header or no ``rel="next"`` link.

        Raises a ``ValueError`` if the ``Link`` header contains a next link but the configured
        ``pagination_parameter_name`` is not found in the link's query string.
        """
        next_page_data: dict[str, Any] = {}

        if "link" not in response.headers:
            return next_page_data

        # Parse RFC 5988 Link header for rel="next"
        next_link = [rel for rel in response.headers["link"].split(",") if 'rel="next"' in rel]
        if not next_link:
            return next_page_data

        # Extract URL and parse query string
        parsed_url = urllib.parse.urlparse(next_link[0].split(";")[0].strip(" <>"))
        query_parameters = urllib.parse.parse_qs(parsed_url.query)

        if self.pagination_parameter_name not in query_parameters:
            raise ValueError(
                f"Expected pagination parameter '{self.pagination_parameter_name}' "
                f"in Link header, but found: {list(query_parameters.keys())}"
            )

        next_page_data[self.pagination_parameter_name] = query_parameters[self.pagination_parameter_name][0]
        return next_page_data
