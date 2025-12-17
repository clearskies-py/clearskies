from typing import TYPE_CHECKING, Any

from clearskies import configs, configurable, decorators, loggable
from clearskies.authentication import Authentication
from clearskies.di import InjectableProperties, inject

if TYPE_CHECKING:
    from gql import Client


class GraphqlClient(configurable.Configurable, loggable.Loggable, InjectableProperties):
    """
    A simple GraphQL client wrapper using gql library.

    This client handles the connection to GraphQL APIs and provides methods to execute
    queries and mutations. It supports authentication, custom headers, and configurable timeouts.

    Example usage:
    ```python
    import clearskies

    client = clearskies.clients.GraphqlClient(
        endpoint="https://api.example.com/graphql",
        authentication=clearskies.authentication.SecretBearer(
            environment_key="API_TOKEN", header_prefix="Bearer "
        ),
        headers={"X-Custom-Header": "value"},
        timeout=30,
    )

    # Execute a query
    result = client.execute('''
        query {
            projects {
                id
                name
            }
        }
    ''')
    ```
    """

    """
    The GraphQL API endpoint URL.

    The full URL to your GraphQL API endpoint. Example:

    ```python
    client = clearskies.clients.GraphqlClient(
        endpoint="https://api.example.com/graphql"
    )
    ```

    Defaults to "http://localhost:4000/graphql" for local development.
    """
    endpoint = configs.String(default="http://localhost:4000/graphql")

    """
    Authentication mechanism for the GraphQL API.

    An instance of a clearskies authentication class that provides credentials for the API.
    The authentication object's headers() method will be called to add authorization headers
    to requests. Example:

    ```python
    client = clearskies.clients.GraphqlClient(
        endpoint="https://api.example.com/graphql",
        authentication=clearskies.authentication.SecretBearer(
            environment_key="GRAPHQL_TOKEN",
            header_prefix="Bearer "
        )
    )
    ```

    Set to None for public APIs that don't require authentication.
    """
    authentication = configs.Authentication(default=None)

    """
    Additional HTTP headers to include in requests.

    A dictionary of header names and values to send with every request. These headers
    are merged with any headers provided by the authentication mechanism. Example:

    ```python
    client = clearskies.clients.GraphqlClient(
        endpoint="https://api.example.com/graphql",
        headers={
            "X-API-Version": "v1",
            "X-Client-Name": "my-app"
        }
    )
    ```

    Defaults to an empty dictionary.
    """
    headers = configs.AnyDict(default={})

    """
    Request timeout in seconds.

    Maximum time to wait for a response from the GraphQL API before raising a timeout error.
    Applies to both connection and read timeouts. Example:

    ```python
    client = clearskies.clients.GraphqlClient(
        endpoint="https://api.example.com/graphql",
        timeout=60  # Wait up to 60 seconds for responses
    )
    ```

    Defaults to 10 seconds.
    """
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
        """
        Get the underlying gql Client instance.

        Lazily creates and caches a gql Client with the configured endpoint, authentication,
        headers, and timeout. The client handles the HTTP transport layer for GraphQL requests.

        This property is primarily used internally by the execute() method, but can be accessed
        directly if you need lower-level control over GraphQL operations.

        Returns:
            Client: A gql Client instance configured with this GraphqlClient's settings.
        """
        from gql import Client
        from gql.transport.requests import RequestsHTTPTransport

        if hasattr(self, "_client"):
            return self._client  # type: ignore

        if self.authentication:
            # Inject dependencies if the authentication object supports it
            if hasattr(self.authentication, "injectable_properties"):
                self.authentication.injectable_properties(self.di)  # type: ignore[attr-defined]
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
