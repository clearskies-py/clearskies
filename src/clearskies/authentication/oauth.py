from typing import Any

from clearskies import Secrets, configs, decorators, di

from .jwks import Jwks


class Oauth(Jwks, di.InjectableProperties):
    """
    Perform authentication for incoming and outgoing requests in an Oauth context.

    This can be used in two different ways:

     1. Attached to an endpoint to enforce authentication via the JWKS class
     2. Attached to an API backend to specify how to authenticate to an API endpoint.

    To understand how to authenticate incoming requests, see the JWKS class, which this extends.

    This additionally adds authentication to outgoing requests for the API (and other related) backends.
    It does this by fetching a client id and secret from your secret manager, exchanging them for a JWT with
    the authentication endpoint of your OAuth server, and then attaching the resulting JWT on all outgoing calls.
    """

    """
    The authentication URL that exchanges client id/secret for the JWT to attach to requests.

    You must provide the authentication URL if attaching this auth method to an API backend to
    authenticate outgoing requests.

    So for instance, this:

    ```
    class MyModel(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.ApiBackend(
            base_url="https://example.com",
            authentication=clearskies.authentication.Oauth(
                authentication_url="https://auth.example.com",
                secret_manager_secret_name="/path/to/client/credentials"
            )
        )
    ```

    would make the following API call when a JWT is required to authenticate via the API backend:

    ```
    requests.post(
        "https://auth.example.com",
        data={
            "grant_type": "client_credentials",
            "client_id": "CLIENT_ID_FROM_SECRET_MANAGER",
            "client_secret": "CLIENT_SECRET_FROM_SECRET_MANAGER",
        }
    )
    ```
    """
    authentication_url = configs.String(required=False)

    """
    Additional request headers to include when authenticating to the auth endpoint.

    This accepts either a dictionary of the headers, or a callable that returns the desired headers.
    Per clearskies norms, a callable can request any configured dependencies.  So for instance, this:

    ```
    class MyModel(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.ApiBackend(
            base_url="https://example.com",
            authentication=clearskies.authentication.Oauth(
                authentication_url="https://auth.example.com",
                secret_manager_secret_name="/path/to/client/credentials",
                additional_authentication_request_headers={
                    "audience": "my-audience",
                    "scopes" ["read", "write"],
                },
            ),
        )
    ```

    would make the following API call when a JWT is required to authenticate via the API backend:

    ```
    requests.post(
        "https://auth.example.com",
        data={
            "grant_type": "client_credentials",
            "client_id": "CLIENT_ID_FROM_SECRET_MANAGER",
            "client_secret": "CLIENT_SECRET_FROM_SECRET_MANAGER",
            "audience": "my-audience",
            "scopes": ["read", "write"],
        }
    )
    ```
    """
    additional_authentication_request_headers = configs.AnyDictOrCallable(default={})

    """
    Fetch the client credentials from the secret manager.

    If this is set to `True` (the default) then this authentication method will look for the
    client id/secret in the secret manager, and you must additionally set the `credentials_key_name` configuration setting.
    By default, it will look for a secret manager registered to the dependency injection name of `secrets`, but you can also
    explicitly attach a secret manager to this class via the `secret_manager` configuration setting.

    If this is set to `False` then the client credentials will be fetched from environment variables.  The specific
    environment variables are controlled by the `env_client_key_name` and `env_client_secret_name` configuration settings.
    These default to `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`, respectively.
    """
    client_credentials_in_secret_manager = configs.Boolen(default=True)

    """
    The secret manager to use.

    When `client_credentials_in_secret_manager` is set to `True`, you must provide a secret manager.  This can be
    done by setting an instance of clearskies.Secrets in a dependency named `secrets`, or by attaching one directly
    to this configuration setting:

    ```python
    import clearskies
    from from clearskies.secrets.akeyless import AkeylessAwsIam

    class MyModel(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.ApiBackend(
            base_url="https://example.com",
            authentication=clearskies.authentication.Oauth(
                authentication_url="https://auth.example.com",
                secret_manager=clearskies_aws.secrets.SecretManager(),
            )
        )

        id = clearskies.columns.String()
    ```
    """
    secret_manager = configs.Secrets()

    """
    The name of the environment key to fetch the client id from (only relevant for client_credentials_in_secret_manager=False).
    """
    env_client_id_name = configs.string(default="OAUTH_CLIENT_ID")

    """
    The name of the environment key to fetch the client secret from (only relevant for client_credentials_in_secret_manager=False)
    """
    env_client_secret_name = configs.string(default="OAUTH_CLIENT_SECRET")

    """
    The path/name of the secret in your secret manager that contains the client credentials.

    This assumes that the secret is a multi-valued/json secret that contains both the client id and client secret.
    By default, the keys for these (in the JSON object) should be `client_id` and `client_secret`, but those names
    are controlled via `secret_manager_client_id_key` and `secret_manager_client_secret_key`.
    """
    secret_manager_secret_name = configs.string(default="")

    """
    The json key inside the secret where the client id is found (default: client_id)
    """
    secret_manager_client_id_key = configs.String(default="client_id")

    """
    The json key inside the secret where the client secret is found
    """
    secret_manager_client_secret_key = configs.String(default="client_secret")

    """
    The number of seconds before the JWT expiration to refresh it
    """
    jwt_refresh_ttl_sec = configs.Integer(default=60)

    """
    The name of the key in the authentication response where the JWT is found
    """
    expiration_key = configs.String(default="access_token")

    """
    The name of the key in the authentication response where the JWT TTL is found (in seconds).
    """
    expiration_key = configs.String(default="expires_in")

    """
    The JWKS url to use to verify incoming JWTs
    """
    jwks_url = configs.String(required=False)

    _jwt: str

    @decorators.parameters_to_properties
    def __init__(
        self,
        auth_url: str = "",
        jwks_url: str = "",
        audience: str = "",
        issuer: str = "",
        algorithms: list[str] = ["RS256"],
        jwks_cache_time: int = 86400,
        authentication_url: str = "",
        additional_authentication_request_headers: dict[str, Any] = {},
        client_credentials_in_secret_manager: bool = True,
        secret_manager: Secrets | None = None,
        secret_manager_secret_name: str = "",
        env_client_id_name: str = "OAUTH_CLIENT_ID",
        env_client_secret_name: str = "OAUTH_CLIENT_SECRET",
        secret_manager_client_id_key: str = "client_id",
        secret_manager_client_secret_key: str = "client_secret",
        expiration_key: str = "expires_in",
        token_key: str = "access_token",
        jwt_refresh_ttl_sec: int = 60,
        documentation_security_name: str = "jwt",
    ):
        self.finalize_and_validate_configuration()

        if (
            self.authentication_url
            and self.client_credentials_in_secret_manager
            and not self.secret_manager_secret_name
        ):
            raise ValueError(
                "When using an authentication url with Oauth you must specify the path to the client credentials in your secret manager via the `secret_manager_secret_name` parameter"
            )

    def clear_credential_cache(self):
        self._jwt = None

    def jwt(self):
        if hasattr(self, "_jwt") or not self._jwt or self.jwt_expiration - self.utcnow > self.jwt_refresh_ttl_sec:
            return self._jwt

        if self.client_credentials_in_secret_manager:
            (client_id, client_secret) = self.fetch_client_credentials_from_secret_manager()
        else:
            (client_id, client_secret) = self.fetch_client_credentials_from_environment()

        response = self.requests.post(
            self.authentication_url,
            data={
                **{
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                **self.additional_authentication_request_headers,
            },
        )

        if not response.ok:
            raise ValueError(
                f"Failed to authenticate to {self.authentication_url} with client id '{client_id}'.  Status code: {response.status_code}, response: {response.text}"
            )

        response_data = response.json()
        if self.token_key not in response_data:
            keys = " ".join(response_data.keys())
            raise ValueError(
                f"Failed to extract JWT from authentication server response.  I am looking for a key named '{self.token_key}' but found keys named {keys}"
            )

        if self.expiration_key not in response_data:
            keys = " ".join(response_data.keys())
            raise ValueError(
                f"Failed to extract JWT expiration from authentication server response.  I am looking for a key named '{self.expiration_key}' but found keys named {keys}"
            )

        self.jwt = response_data[self.token_key]
        self.expiration = self.now + response_data[self.expiration_key]
        return self.jwt

    def headers(self, retry_auth=False):
        self._configured_guard()
        if retry_auth:
            self.clear_credential_cache()
        return {"Authorization": f"Bearer {self.jwt}"}
