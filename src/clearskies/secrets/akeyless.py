from __future__ import annotations

import json
from types import ModuleType
from typing import TYPE_CHECKING, Any

from clearskies import configs, secrets
from clearskies.decorators import parameters_to_properties
from clearskies.di import inject
from clearskies.functional.json import get_nested_attribute
from clearskies.secrets.cache_storage.secret_cache import SecretCache
from clearskies.secrets.exceptions import PermissionsError

if TYPE_CHECKING:
    from akeyless import ListItemsOutput, V2Api  # type: ignore[import-untyped]


class Akeyless(secrets.Secrets):
    """
    Backend for managing secrets using the Akeyless Vault.

    This class provides integration with Akeyless vault services, allowing you to store, retrieve,
    and manage secrets. It supports different types of secrets (static, dynamic, rotated) and
    includes authentication mechanisms for AWS IAM, SAML, and JWT.

    ### Token Validation and Caching

    Authentication tokens are automatically cached and validated to minimize API calls:
    - All auth methods (AWS IAM, JWT, SAML) cache the token's `expiry` timestamp from the auth API response
    - **SAML**: First checks credentials file for cached token before API call (most efficient)
    - **JWT/AWS IAM**: Caches token and expiry from API auth response
    - Tokens are automatically refreshed when expired or within 10 seconds of expiry

    ### Cache Storage

    The `cache_storage` parameter (inherited from `Secrets`) accepts an instance of a subclass of
    [`SecretCache`](src/clearskies/secrets/cache_storage/secret_cache.py:1).
    This enables caching secrets in external stores like AWS Parameter Store, AWS Secrets Manager,
    Redis, etc.

    #### Example: Using Cache Storage

    ```python
    from clearskies.secrets.cache_storage import SecretCache
    import clearskies


    class MyCache(SecretCache):
        def get(self, path: str) -> str | None:
            # Retrieve from your cache
            return None

        def set(self, path: str, value: str, ttl: int | None = None) -> None:
            # Store in your cache
            pass

        def delete(self, path: str) -> None:
            # Remove from your cache
            pass

        def clear(self) -> None:
            # Clear all cached secrets
            pass


    secrets = clearskies.secrets.Akeyless(
        access_id="p-abc123",
        access_type="aws_iam",
        cache_storage=MyCache(),
    )
    # First call fetches from Akeyless and caches
    secret_value = secrets.get("/path/to/secret")
    # Subsequent calls return from cache
    secret_value = secrets.get("/path/to/secret")
    # Force refresh from Akeyless
    secret_value = secrets.get("/path/to/secret", refresh=True)
    ```
    """

    """
    HTTP client for making API requests
    """
    requests = inject.Requests()

    """
    Environment configuration for retrieving environment variables
    """
    environment = inject.Environment()

    """
    The current time provider for testability
    """
    now = inject.Now()

    """
    The Akeyless SDK module injected by the dependency injection system
    """
    akeyless: ModuleType = inject.ByName("akeyless_sdk")  # type: ignore

    """
    The access ID for the Akeyless service

    This must match the pattern p-[0-9a-zA-Z]+ (e.g., "p-abc123")
    """
    access_id = configs.String(required=True, regexp=r"^p-[\d\w]+$")

    """
    The authentication method to use

    Must be one of "aws_iam", "saml", or "jwt"
    """
    access_type = configs.Select(["aws_iam", "saml", "jwt"], required=True)

    """
    The Akeyless API host to connect to

    Defaults to "https://api.akeyless.io"
    """
    api_host = configs.String(default="https://api.akeyless.io")

    """
    The environment variable key that contains the JWT when using JWT authentication

    This is required when access_type is "jwt"
    """
    jwt_env_key = configs.String(required=False)

    """
    The SAML profile name when using SAML authentication

    Must match the pattern [0-9a-zA-Z-]+ if provided
    """
    profile = configs.String(regexp=r"^[\d\w-]+$", default="default")

    """
    Whether to automatically guess the secret type

    When enabled, the system will check the secret type (static, dynamic, rotated)
    and call the appropriate method to retrieve it.
    """
    auto_guess_type = configs.Boolean(default=False)

    """
    When the current token expires (Unix timestamp in seconds)
    """
    _token_expiry: float

    """
    The current authentication token
    """
    _token: str

    """
    The configured V2Api client
    """
    _api: V2Api

    @parameters_to_properties
    def __init__(
        self,
        access_id: str,
        access_type: str,
        jwt_env_key: str | None = None,
        api_host: str | None = None,
        profile: str | None = None,
        auto_guess_type: bool = False,
        cache_storage: SecretCache | None = None,
    ):
        """
        Initialize the Akeyless backend with the specified configuration.

        The access_id must be provided and follow the format p-[0-9a-zA-Z]+. The access_type must be
        one of "aws_iam", "saml", or "jwt". If using JWT authentication, jwt_env_key must be provided.
        """
        self.finalize_and_validate_configuration()

    def configure(self) -> None:
        """
        Perform additional configuration validation.

        Ensures that when using JWT authentication, the jwt_env_key is provided. Raises ValueError
        if access_type is "jwt" and jwt_env_key is not provided.
        """
        if self.access_type == "jwt" and not self.jwt_env_key:
            raise ValueError("When using the JWT access type for Akeyless you must provide jwt_env_key")

    @property
    def api(self) -> V2Api:
        """
        Get the configured V2Api client.

        Creates a new API client if one doesn't exist yet, using the configured api_host.
        """
        if not hasattr(self, "_api"):
            configuration = self.akeyless.Configuration(host=self.api_host)
            self._api = self.akeyless.V2Api(self.akeyless.ApiClient(configuration))
        return self._api

    def create(self, path: str, value: Any) -> bool:
        """
        Create a new secret at the given path.

        Checks permissions before creating the secret and raises PermissionsError if the user doesn't
        have write permission for the path. The value is converted to a string before storage.
        """
        if not "write" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission the secret '{path}'")

        res = self.api.create_secret(self.akeyless.CreateSecret(name=path, value=str(value), token=self._get_token()))

        # Update cache with new value
        if self.cache:
            self.cache.set(path, str(value))

        return True

    def get(
        self,
        path: str,
        silent_if_not_found: bool = False,
        refresh: bool = False,
        json_attribute: str | None = None,
        args: dict[str, Any] | None = None,
    ) -> str:
        """
        Get the secret at the given path.

        When cache_storage is configured and refresh is False, this method first checks the cache
        for the secret. If found, it returns the cached value. If not found or refresh is True,
        it fetches from Akeyless and stores in the cache.

        When auto_guess_type is enabled, this method automatically determines if the secret is static,
        dynamic, or rotated and calls the appropriate method to retrieve it. If silent_if_not_found is
        True, returns an empty string when the secret is not found. If json_attribute is provided,
        treats the secret as JSON and returns the specified attribute.
        """
        # Check cache first if not forcing refresh
        if not refresh and self.cache:
            cached_value = self.cache.get(path)
            if cached_value is not None:
                return cached_value

        # Fetch from Akeyless - sub-methods handle caching, so we don't need to cache here
        if not self.auto_guess_type:
            return self.get_static_secret(
                path, silent_if_not_found=silent_if_not_found, json_attribute=json_attribute, refresh=True
            )
        else:
            try:
                secret = self.describe_secret(path)
            except Exception as e:
                if e.status == 404:  # type: ignore
                    if silent_if_not_found:
                        return ""
                    raise e
                else:
                    raise ValueError(
                        f"describe-secret call failed for path {path}: perhaps a permissions issue?  Akeless says {e}"
                    )

            self.logger.debug(f"Auto-detected secret type '{secret.item_type}' for secret '{path}'")
            match secret.item_type.lower():
                case "dynamic_secret":
                    return str(
                        self.get_dynamic_secret(
                            path,
                            json_attribute=json_attribute,
                            args=args,
                            refresh=True,
                        )
                    )
                case "rotated_secret":
                    return str(self.get_rotated_secret(path, json_attribute=json_attribute, args=args, refresh=True))
                case "static_secret":
                    return self.get_static_secret(
                        path, json_attribute=json_attribute, silent_if_not_found=silent_if_not_found, refresh=True
                    )
                case _:
                    raise ValueError(f"Unsupported secret type for auto-detection: '{secret.item_type}'")

    def get_static_secret(
        self,
        path: str,
        silent_if_not_found: bool = False,
        refresh: bool = False,
        json_attribute: str | None = None,
    ) -> str:
        """
        Get a static secret from the given path.

        When cache_storage is configured and refresh is False, this method first checks the cache
        for the secret. If found, it returns the cached value. If not found or refresh is True,
        it fetches from Akeyless and stores in the cache.

        Checks permissions before retrieving the secret and raises PermissionsError if the user doesn't
        have read permission. If silent_if_not_found is True, returns an empty string when the secret
        is not found. If json_attribute is provided, treats the secret as JSON and returns the specified attribute.
        """
        # Check cache first if not forcing refresh
        if not refresh and self.cache:
            cached_value = self.cache.get(path)
            if cached_value is not None:
                return cached_value

        if not "read" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission the secret '{path}'")

        try:
            res: dict[str, object] = self.api.get_secret_value(  # type: ignore
                self.akeyless.GetSecretValue(
                    names=[path], token=self._get_token(), json=True if json_attribute else False
                )
            )
        except Exception as e:
            if e.status == 404:  # type: ignore
                if silent_if_not_found:
                    return ""
                raise KeyError(f"Secret '{path}' not found")
            raise e

        if json_attribute:
            value = get_nested_attribute(res[path], json_attribute)  # type: ignore
        else:
            value = str(res[path])

        # Store in cache if configured and we got a value
        if value and self.cache:
            self.cache.set(path, value)

        return value

    def get_dynamic_secret(
        self,
        path: str,
        json_attribute: str | None = None,
        args: dict[str, Any] | None = None,
        refresh: bool = False,
    ) -> Any:
        """
        Get a dynamic secret from the given path.

        When cache_storage is configured and refresh is False, this method first checks the cache
        for the secret. If found, it returns the cached value. If not found or refresh is True,
        it fetches from Akeyless and stores in the cache.

        Dynamic secrets are generated on-demand, such as database credentials. Checks permissions
        before retrieving the secret and raises PermissionsError if the user doesn't have read
        permission. If json_attribute is provided, treats the result as JSON and returns the
        specified attribute.
        """
        # Check cache first if not forcing refresh
        if not refresh and self.cache:
            cached_value = self.cache.get(path)
            if cached_value is not None:
                return cached_value

        if not "read" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission the secret '{path}'")

        kwargs = {
            "name": path,
            "token": self._get_token(),
        }
        if args:
            kwargs["args"] = args  # type: ignore
        res: dict[str, Any] = self.api.get_dynamic_secret_value(self.akeyless.GetDynamicSecretValue(**kwargs))  # type: ignore

        if json_attribute:
            value = get_nested_attribute(res, json_attribute)
        else:
            value = res

        # Store in cache if configured and we got a value
        if value and self.cache:
            cache_value = value if isinstance(value, str) else json.dumps(value)
            self.cache.set(path, cache_value)

        return value

    def get_rotated_secret(
        self,
        path: str,
        json_attribute: str | None = None,
        args: dict[str, Any] | None = None,
        refresh: bool = False,
    ) -> Any:
        """
        Get a rotated secret from the given path.

        When cache_storage is configured and refresh is False, this method first checks the cache
        for the secret. If found, it returns the cached value. If not found or refresh is True,
        it fetches from Akeyless and stores in the cache.

        Rotated secrets are automatically replaced on a schedule. Checks permissions before
        retrieving the secret and raises PermissionsError if the user doesn't have read
        permission. If json_attribute is provided, treats the result as JSON and returns the
        specified attribute.
        """
        # Check cache first if not forcing refresh
        if not refresh and self.cache:
            cached_value = self.cache.get(path)
            if cached_value is not None:
                return cached_value

        if not "read" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission the secret '{path}'")

        kwargs = {
            "names": path,
            "token": self._get_token(),
            "json": True if json_attribute else False,
        }
        if args:
            kwargs["args"] = args  # type: ignore

        res: dict[str, str] = self._api.get_rotated_secret_value(self.akeyless.GetRotatedSecretValue(**kwargs))["value"]  # type: ignore

        if json_attribute:
            value = get_nested_attribute(res, json_attribute)
        else:
            value = res

        # Store in cache if configured and we got a value
        if value and self.cache:
            cache_value = value if isinstance(value, str) else json.dumps(value)
            self.cache.set(path, cache_value)

        return value

    def describe_secret(self, path: str) -> Any:
        """
        Get metadata about a secret.

        Checks permissions before retrieving metadata and raises PermissionsError if the user
        doesn't have read permission for the path.
        """
        if not "read" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission the secret '{path}'")

        return self.api.describe_item(self.akeyless.DescribeItem(name=path, token=self._get_token()))

    def list_secrets(self, path: str) -> list[Any]:
        """
        List all secrets at the given path.

        Checks permissions before listing secrets and raises PermissionsError if the user doesn't
        have list permission for the path. Returns an empty list if no secrets are found.
        """
        if not "list" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission the secrets in '{path}'")

        res: ListItemsOutput = self.api.list_items(  # type: ignore
            self.akeyless.ListItems(
                path=path,
                token=self._get_token(),
            )
        )
        if not res.items:
            return []

        return [item.item_name for item in res.items]

    def update(self, path: str, value: Any) -> None:
        """
        Update an existing secret.

        Checks permissions before updating the secret and raises PermissionsError if the user
        doesn't have write permission for the path. The value is converted to a string before storage.
        Also updates the cache if cache_storage is configured.
        """
        if not "write" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission the secret '{path}'")

        res = self.api.update_secret_val(
            self.akeyless.UpdateSecretVal(name=path, value=str(value), token=self._get_token())
        )

        # Update cache with new value
        if self.cache:
            self.cache.set(path, str(value))

    def upsert(self, path: str, value: Any) -> None:
        """
        Create or update a secret.

        This method attempts to update an existing secret, and if that fails, it tries to create
        a new one. The value is converted to a string before storage.
        Also updates the cache if cache_storage is configured.
        """
        try:
            self.update(path, value)
        except Exception as e:
            self.create(path, value)

    def list_sub_folders(self, main_folder: str) -> list[str]:
        """
        Return the list of secrets/sub folders in the given folder.

        Checks permissions before listing subfolders and raises PermissionsError if the user doesn't
        have list permission for the path. Returns the relative subfolder names without the parent path.
        """
        if not "list" in self.describe_permissions(main_folder):
            raise PermissionsError(f"You do not have permission to list sub folders in '{main_folder}'")

        items = self.api.list_items(self.akeyless.ListItems(path=main_folder, token=self._get_token()))

        # akeyless will return the absolute path and end in a slash but we only want the folder name
        main_folder_string_len = len(main_folder)
        return [sub_folder[main_folder_string_len:-1] for sub_folder in items.folders]  # type: ignore

    def get_ssh_certificate(self, cert_issuer: str, cert_username: str, path_to_public_file: str) -> Any:
        """
        Get an SSH certificate from Akeyless.

        Reads the public key from the specified file path and requests a certificate for the given
        username and issuer from Akeyless.
        """
        with open(path_to_public_file, "r") as fp:
            public_key = fp.read()

        res = self.api.get_ssh_certificate(
            self.akeyless.GetSSHCertificate(
                cert_username=cert_username,
                cert_issuer_name=cert_issuer,
                public_key_data=public_key,
                token=self._get_token(),
            )
        )

        return res.data  # type: ignore

    def delete(self, path: str) -> bool:
        """
        Delete a secret at the given path.

        Checks permissions before deleting and raises PermissionsError if the user doesn't
        have delete permission for the path. Also removes the secret from cache if cache_storage
        is configured.
        """
        if not "delete" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission to delete the secret '{path}'")

        delete = self.api.delete_item(self.akeyless.DeleteItem(name=path, token=self._get_token()))

        # Remove from cache
        if self.cache:
            self.cache.delete(path)

        return delete.item_name == path

    def _get_token(self) -> str:
        """
        Get an authentication token for Akeyless API calls.

        Returns a cached token if available and not expired (within 10 seconds), otherwise obtains
        a new one using the configured authentication method. Token expiry is retrieved from the
        auth response to ensure accurate validation.
        """
        # Check if we have a valid cached token
        if hasattr(self, "_token_expiry") and hasattr(self, "_token"):
            current_timestamp = self.now.timestamp()
            # Add a 10 second buffer to avoid using tokens that are about to expire
            if current_timestamp < (self._token_expiry - 10):
                self.logger.debug(f"Using cached token (expires at {self._token_expiry})")
                return self._token
            else:
                self.logger.debug(
                    f"Cached token expired or expiring soon (expiry: {self._token_expiry}, current: {current_timestamp})"
                )

        auth_method_name = f"auth_{self.access_type}"
        if not hasattr(self, auth_method_name):
            raise ValueError(f"Requested Akeyless authentication with unsupported auth method: '{self.access_type}'")

        # Call auth method which returns (token, expiry)
        auth_result = getattr(self, auth_method_name)()

        # Handle both tuple (token, expiry) and string (token only) responses
        if isinstance(auth_result, tuple):
            self._token, self._token_expiry = auth_result
        else:
            # Fallback for legacy: token only, no expiry returned
            self._token = auth_result
            # Set expiry to 30 minutes from now as fallback
            self._token_expiry = self.now.timestamp() + 1800  # 30 minutes
            self.logger.warning(f"Auth method {auth_method_name} did not return expiry, using 30-minute fallback")

        return self._token

    def _is_token_valid(self, token: str) -> bool:
        """
        Check if a token is still valid by making a test API call.

        This validates that the token has not expired and can still be used for API calls.
        Returns True if the token is valid, False otherwise.
        """
        try:
            # Make a lightweight API call to validate the token
            self.api.describe_permissions(self.akeyless.DescribePermissions(token=token, path="/", type="item"))
            return True
        except Exception as e:
            # Token is invalid or expired
            self.logger.debug(f"Token validation failed: {e}")
            return False

    def auth_aws_iam(self):
        """
        Authenticate using AWS IAM.

        Uses the akeyless_cloud_id package to generate a cloud ID and authenticates with Akeyless
        using the configured access_id. Returns a tuple of (token, expiry_timestamp).
        """
        from akeyless_cloud_id import CloudId  # type: ignore

        res = self.api.auth(
            self.akeyless.Auth(access_id=self.access_id, access_type="aws_iam", cloud_id=CloudId().generate())
        )
        # Return tuple of (token, expiry)
        return (res.token, res.expiry)  # type: ignore

    def auth_saml(self):
        """
        Authenticate using SAML.

        Uses the akeyless CLI to generate credentials and then retrieves a token either directly
        from the credentials file or by making an API call to convert the credentials to a token.
        Validates that the returned token is still valid before returning it by checking the
        expiry timestamp in the credentials file.
        Returns a tuple of (token, expiry_timestamp).
        """
        import json
        import os
        from pathlib import Path

        os.system(f"akeyless list-items --profile {self.profile} --path /not/a/real/path > /dev/null 2>&1")
        home = str(Path.home())
        with open(f"{home}/.akeyless/.tmp_creds/{self.profile}-{self.access_id}", "r") as creds_file:
            credentials = creds_file.read()
            credentials_json = json.loads(credentials)

        # Check if credentials file has a cached token
        if "token" in credentials_json:
            token = credentials_json["token"]

            # Check expiry if present (Unix timestamp in seconds)
            if "expiry" in credentials_json:
                expiry_timestamp = credentials_json["expiry"]
                # Convert datetime to Unix timestamp for comparison
                current_timestamp = self.now.timestamp()
                # Add a 10 second buffer to avoid using tokens that are about to expire
                if current_timestamp < (expiry_timestamp - 10):
                    self.logger.debug(f"Using cached SAML token (expires at {expiry_timestamp})")
                    return (token, expiry_timestamp)
                else:
                    self.logger.debug(
                        f"Cached SAML token expired or expiring soon (expiry: {expiry_timestamp}, current: {current_timestamp})"
                    )
            else:
                # No expiry field, validate with API call as fallback
                self.logger.debug("No expiry field in credentials, validating token via API")
                if self._is_token_valid(token):
                    # Use 30 minutes as fallback expiry if not provided
                    fallback_expiry = self.now.timestamp() + 1800
                    return (token, fallback_expiry)

        # Get a new token using static-creds-auth
        self.logger.debug("Fetching new SAML token via static-creds-auth")
        response = self.requests.post(
            "https://rest.akeyless.io/",
            data={
                "cmd": "static-creds-auth",
                "access-id": self.access_id,
                "creds": credentials.strip(),
            },
        )
        response_json = response.json()
        # Return tuple of (token, expiry)
        return (response_json["token"], response_json.get("expiry", self.now.timestamp() + 1800))

    def auth_jwt(self):
        """
        Authenticate using JWT.

        Retrieves the JWT from the environment variable specified by jwt_env_key and authenticates
        with Akeyless. Raises ValueError if jwt_env_key is not specified.
        Returns a tuple of (token, expiry_timestamp).
        """
        if not self.jwt_env_key:
            raise ValueError(
                "To use AKeyless JWT Auth, "
                "you must specify the name of the ENV key to load the JWT from when configuring AKeyless"
            )
        res = self.api.auth(
            self.akeyless.Auth(access_id=self.access_id, access_type="jwt", jwt=self.environment.get(self.jwt_env_key))
        )
        # Return tuple of (token, expiry)
        return (res.token, res.expiry)  # type: ignore

    def describe_permissions(self, path: str, type: str = "item") -> list[str]:
        """
        List permissions for a path.

        Returns a list of permission strings (e.g., "read", "write", "list") that the current
        authentication token has for the specified path.
        """
        return self.api.describe_permissions(
            self.akeyless.DescribePermissions(token=self._get_token(), path=path, type=type)
        ).client_permissions  # type: ignore


class AkeylessSaml(Akeyless):
    """Convenience class for SAML authentication with Akeyless."""

    def __init__(self, access_id: str, api_host: str = "", profile: str = ""):
        """
        Initialize with SAML authentication.

        Sets access_type to "saml" and passes the remaining parameters to the parent class.
        """
        return super().__init__(access_id, "saml", api_host=api_host, profile=profile)


class AkeylessJwt(Akeyless):
    """Convenience class for JWT authentication with Akeyless."""

    def __init__(self, access_id: str, jwt_env_key: str = "", api_host: str = "", profile: str = ""):
        """
        Initialize with JWT authentication.

        Sets access_type to "jwt" and passes the remaining parameters to the parent class.
        """
        return super().__init__(access_id, "jwt", jwt_env_key=jwt_env_key, api_host=api_host, profile=profile)


class AkeylessAwsIam(Akeyless):
    """Convenience class for AWS IAM authentication with Akeyless."""

    def __init__(self, access_id: str, api_host: str = ""):
        """
        Initialize with AWS IAM authentication.

        Sets access_type to "aws_iam" and passes the remaining parameters to the parent class.
        """
        return super().__init__(access_id, "aws_iam", api_host=api_host)
