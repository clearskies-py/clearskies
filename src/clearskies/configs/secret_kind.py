from __future__ import annotations

from clearskies.configs import select


class SecretKind(select.Select):
    """
    Specify the type of secret being retrieved from a secrets manager.

    The secret kind determines which retrieval method is used. When an explicit kind is provided,
    it skips the type detection call and directly retrieves the secret as that type. This is particularly
    useful with Akeyless, where specifying the kind avoids the describe_secret() API call.

    The allowed kinds are:

      1. `static_secret` — A static secret that doesn't change (default)
      2. `dynamic_secret` — A dynamically generated secret (e.g., temporary database credentials)
      3. `rotated_secret` — A secret that is automatically rotated on a schedule

    When used with SecretBearer authentication, specify the kind to optimize secret retrieval:

    ```python
    import clearskies

    # Static secret (default, no auto-detection)
    authentication = clearskies.authentication.SecretBearer(
        secret_key="/path/to/api/key",
        secret_kind="static_secret",
    )

    # Dynamic secret - skips describe_secret() call
    authentication = clearskies.authentication.SecretBearer(
        secret_key="/path/to/db/credentials",
        secret_kind="dynamic_secret",
        refresh=True,  # Always fetch fresh credentials
    )

    # Dynamic secret with JSON extraction
    authentication = clearskies.authentication.SecretBearer(
        secret_key="/path/to/credentials",
        secret_kind="dynamic_secret",
        json_path="password",  # Extract specific field
        refresh=True,
    )

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.Callable(
            lambda: {"hello": "world"},
            authentication=authentication,
        )
    )
    wsgi()
    ```

    When kind is not provided and `auto_guess_type=True` is configured on the secrets backend,
    the backend will auto-detect the secret type by querying metadata. Defaults to `static_secret`
    if neither kind is provided nor auto-detection is enabled.
    """

    STATIC = "static_secret"
    DYNAMIC = "dynamic_secret"
    ROTATED = "rotated_secret"

    ALL_KINDS = [STATIC, DYNAMIC, ROTATED]

    def __init__(self, required=False, default=None):
        super().__init__(self.ALL_KINDS, required=required, default=default)
