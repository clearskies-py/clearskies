from clearskies import configs, decorators, di

from .jwks import Jwks


class Oauth(Jwks, di.InjectableProperties):
    """
    Perform authentication for incoming and outgoing requests in an Oauth context.

    This can be used in two different ways:

     1. Attached to an endpoint to enforce authentication via the JWKS class
     2. Attached to an API backend to specify how to authenticate to an API endpoint.

    To understand how to authenticate incoming requests, see the JWKS class, which this extends.

    This additionally adds authentcation to outgoing requests for the API (and other related) backends.
    It does this by fetching a client id and secret from your secret manager, exchanging them for a JWT with
    the authentication endpoint of your OAuth server, and then attaching the resulting JWT on all outgoing calls.
    """

    """
    The authentication URL that exchanges client id/secret for the JWT to attach to requests.

    You must provide the authentication URL if attaching this auth method to an API backend to
    authenticate outgoing requests.
    """
    auth_url = configs.String(required=False)

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
                auth_url="https://auth.example.com",
                secret_manager=clearskies.
            )
        )

        id = clearskies.columns.String()
    ```
    """
    secret_manager = configs.Secrets()

    """
    The name of the environment key to fetch the client id from (only relevant for client_credentials_in_secret_manager=False).
    """
    env_client_key_name = configs.string(default="OAUTH_CLIENT_ID")

    """
    The name of the environment key to fetch the client secret from (only relevant for client_credentials_in_secret_manager=False)
    """
    env_client_secret_name = configs.string(default="OAUTH_CLIENT_SECRET")

    jwks_url = configs.String(required=False)

    @decorators.parameters_to_properties
    def __init__(
        self,
        auth_url: str = "",
        jwks_url: str = "",
        audience: str = "",
        issuer: str = "",
        algorithms: list[str] = ["RS256"],
        jwks_cache_time: int = 86400,
        authorization_url: str = "",
        documentation_security_name: str = "jwt",
    ):
        self.finalize_and_validate_configuration()

    def clear_credential_cache(self):
        ###################
        ############ HERE!!!!

    def headers(self, retry_auth=False):
        self._configured_guard()
        if retry_auth:
            self.clear_credential_cache()
        return {"Authorization": f"{self.header_prefix}{self.secret}"}
