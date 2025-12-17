from typing import TYPE_CHECKING, Any

from clearskies import configs, configurable, decorators, loggable
from clearskies.authentication import Authentication
from clearskies.di import InjectableProperties, inject

if TYPE_CHECKING:
    from gql import Client


class GraphqlClient(configurable.Configurable, loggable.Loggable, InjectableProperties):
    """
    A simple GraphQL client wrapper using gql library.

    Configurable properties:
    - endpoint: The GraphQL API endpoint URL.
    - authentication: An authentication mechanism (e.g., token-based).
    - headers: Additional headers to include in requests.
    - timeout: Request timeout in seconds.
    """

    endpoint = configs.String(default="http://localhost:4000/graphql")
    authentication = configs.Authentication(default=None)  # Should be of type Authentication
    headers = configs.AnyDict(default={})
    timeout = configs.Integer(default=10)
    di = inject.Di()

    _client: Any

    @decorators.parameters_to_properties
    def __init__(
        self,
        endpoint="http://localhost:4000/graphql",
        headers={},
        authentication: Authentication | None = None,
        timeout=10,
    ):
        self.finalize_and_validate_configuration()

    @property
    def client(self) -> "Client":
        from gql import Client
        from gql.transport.requests import RequestsHTTPTransport

        if hasattr(self, "_client"):
            return self._client  # type: ignore

        if self.authentication:
            # Inject dependencies if the authentication object supports it
            if hasattr(self.authentication, "injectable_properties"):
                self.authentication.injectable_properties(self.di)  # type: ignore[attr-defined]
            self.headers.update(self.authentication.headers())
        transport = RequestsHTTPTransport(
            url=self.endpoint,
            headers=self.headers,
            auth=self.authentication,
            timeout=self.timeout,
        )
        self._client = Client(transport=transport, fetch_schema_from_transport=False)
        return self._client

    def execute(self, query: str, variable_values: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute a GraphQL query or mutation.

        Args:
            query (str): The GraphQL query or mutation string.
            variable_values (dict, optional): Variables for the query/mutation. Defaults to None
        Returns:
            dict: The response data from the GraphQL API.
        """
        from gql import gql

        client = self.client
        prepared_query = gql(query)
        self.logger.debug(
            f"Executing GraphQL query: {prepared_query} on endpoint: {self.endpoint} with variables: {variable_values}"
        )
        result = client.execute(prepared_query, variable_values=variable_values)
        self.logger.debug(f"GraphQL response: {result}")
        return result
