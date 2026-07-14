from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING, Any

from clearskies import configs, decorators, di

from .jwks import Jwks

if TYPE_CHECKING:
    from clearskies.secrets import Secrets


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
    client_credentials_in_secret_manager = configs.Boolean(default=True)

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
    secret_manager = configs.Secrets(default=None)

    """
    The name of the environment key to fetch the client id from (only relevant for client_credentials_in_secret_manager=False).
    """
    env_client_id_name = configs.String(default="OAUTH_CLIENT_ID")

    """
    The name of the environment key to fetch the client secret from (only relevant for client_credentials_in_secret_manager=False)
    """
    env_client_secret_name = configs.String(default="OAUTH_CLIENT_SECRET")

    """
    The path/name of the secret in your secret manager that contains the client credentials.

    This assumes that the secret is a multi-valued/json secret that contains both the client id and client secret.
    By default, the keys for these (in the JSON object) should be `client_id` and `client_secret`, but those names
    are controlled via `secret_manager_client_id_key` and `secret_manager_client_secret_key`.
    """
    secret_manager_secret_name = configs.String(default="")

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
    token_key = configs.String(default="access_token")

    """
    The name of the key in the authentication response where the JWT TTL is found (in seconds).
    """
    expiration_key = configs.String(default="expires_in")

    """
    The JWKS url to use to verify incoming JWTs
    """
    jwks_url = configs.String(required=False)

    secrets = di.inject.Secrets()
    di = di.inject.Di()

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
        delattr(self, "_jwt")

    @property
    def jwt(self) -> str:
        if hasattr(self, "_jwt") and self.expiration - self.now > self.jwt_refresh_ttl_sec:
            return self._jwt

        if self.client_credentials_in_secret_manager:
            (client_id, client_secret) = self.fetch_client_credentials_from_secret_manager()
        else:
            (client_id, client_secret) = self.fetch_client_credentials_from_environment()

        more_headers = {}
        if self.additional_authentication_request_headers:
            if callable(self.additional_authentication_request_headers):
                more_headers = self.di.call_function(self.additional_authentication_request_headers)
                if not isinstance(more_headers, dict):
                    raise ValueError(
                        f"I called the callable attached to '{self.__class__.__name__}.additional_authentication_request_headers' but it returned an object of type '{more_headers.__class__.__name__}'.  It must return a dict[str, str]."
                    )
                for key, value in more_headers.items():
                    if not isinstance(key, str) or not isinstance(key, str):
                        raise ValueError(
                            f"I called the callable attached to '{self.__class__.__name__}.additional_authentication_request_headers' which must return a dict[str, str].  It returned a dictionary with non-string keys/values."
                        )
            else:
                more_headers = self.additional_authentication_request_headers

        response = self.requests.post(
            self.authentication_url,
            data={
                **{
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                **more_headers,
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

        self._jwt = response_data[self.token_key]
        self.expiration = self.now + datetime.timedelta(seconds=response_data[self.expiration_key])
        return self._jwt

    def fetch_client_credentials_from_environment(self) -> tuple[str, str]:
        """
        Fetch client credentials from the environment.

        This is called when self.client_credentials_in_secret_manager is set to `False`.  It pulls the client id and client secret
        from the environment in variables named `self.env_client_id_name` and `self.env_client_id_name`.  Since these come from
        the environment, automatic secret rotation is not supported.
        """
        client_id = self.environment.get(self.env_client_id_name, silent=True)
        if not client_id:
            raise ValueError(
                f"Failed to fetch client id from environment.  Environment variable '{self.env_client_id_name}' was empty."
            )
        client_secret = self.environment.get(self.env_client_secret_name, silent=True)
        if not client_secret:
            raise ValueError(
                f"Failed to fetch client secret from environment.  Environment variable '{self.env_client_secret_name}' was empty."
            )

        return (client_id, client_secret)

    def fetch_client_credentials_from_secret_manager(self) -> tuple[str, str]:
        """
        Fetch client credentials from the secret manager.

        The client credentials are not cached at all, but are fetched anew everytime a new JWT is required.
        As a result, automatic credential rotation is supported out of the box: if the client credentials are rotated
        in the secret manager, then the new credentials will automatically be used the next time the JWT expires.

        This assumes that there is a single secret that contains both the client id and the client secret as a multi-valued/json
        secret.  The path to the secret itself must be set in `self.secret_manager_secret_name` and then you must provide the
        name of the keys where the client id and client secret are stored (via `self.secret_manager_client_id_key`and
        `self.secret_manager_client_secret_key`).
        """
        if self.secret_manager:
            secret = self.secret_manager.get(self.secret_manager_secret_name, silent_if_not_found=True)
            if not secret:
                raise ValueError(
                    f"I fetched the secret named '{self.secret_manager_secret_name}' from the secret manager provided of type '{self.secret_manager.__class__.__name__}' but the secret was empty."
                )
        else:
            secret = self.secrets.get(self.secret_manager_secret_name, silent_if_not_found=True)
            if not secret:
                raise ValueError(
                    f"I fetched the secret named '{self.secret_manager_secret_name}' from the default secret manager of type '{self.secret_manager.__class__.__name__}' but the secret was empty."
                )

        if isinstance(secret, str):
            try:
                secret = json.loads(secret)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"I fetched the secret named '{self.secret_manager_secret_name}' successfully but it did not contain a multi-valued/json secret.  I received a string which was not valid JSON."
                )

        if not isinstance(secret, dict):
            raise ValueError(
                f"I fetched the secret named '{self.secret_manager_secret_name}' successfully but it was an object of type '{secret.__class__.__name__}', while I reqiure a dict."
            )
        for required_key in [self.secret_manager_client_id_key, self.secret_manager_client_secret_key]:
            if required_key not in secret:
                raise KeyError(
                    f"I successfully fetched the secret named '{self.secret_manager_secret_name}' but it did not contain a key called '{required_key}'"
                )
            if not secret.get(required_key):
                raise KeyError(
                    f"I successfully fetched the secret named '{self.secret_manager_secret_name}' but the key '{required_key}' was empty"
                )
            if not isinstance(secret.get(required_key), str):
                raise KeyError(
                    f"I successfully fetched the secret named '{self.secret_manager_secret_name}' but the key '{required_key}' did not contain a string"
                )

        return (secret[self.secret_manager_client_id_key], secret[self.secret_manager_client_secret_key])

    def headers(self, retry_auth=False):
        if retry_auth:
            self.clear_credential_cache()
        return {"Authorization": f"Bearer {self.jwt}"}
