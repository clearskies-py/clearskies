from __future__ import annotations

import datetime
import logging
from types import ModuleType
from typing import TYPE_CHECKING, Any

from clearskies import configs, secrets
from clearskies.decorators import parameters_to_properties
from clearskies.di import inject
from clearskies.functional.json import get_nested_attribute
from clearskies.secrets.exceptions import PermissionsError

if TYPE_CHECKING:
    from akeyless import ListItemsOutput, V2Api  # type: ignore[import-untyped]


class Akeyless(secrets.Secrets):
    """
    Backend for managing secrets using the Akeyless Vault.

    This class provides integration with Akeyless vault services, allowing you to store, retrieve,
    and manage secrets. It supports different types of secrets (static, dynamic, rotated) and
    includes authentication mechanisms for AWS IAM, SAML, and JWT.
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
    When the current token expires
    """
    _token_refresh: datetime.datetime  # type: ignore

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
    ):
        """
        Initialize the Akeyless backend with the specified configuration.

        The access_id must be provided and follow the format p-[0-9a-zA-Z]+. The access_type must be
        one of "aws_iam", "saml", or "jwt". If using JWT authentication, jwt_env_key must be provided.
        """
        self.finalize_and_validate_configuration()
        self.logger = logging.getLogger(self.__class__.__name__)

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
        return True

    def get(
        self,
        path: str,
        silent_if_not_found: bool = False,
        json_attribute: str | None = None,
        args: dict[str, Any] | None = None,
    ) -> str:
        """
        Get the secret at the given path.

        When auto_guess_type is enabled, this method automatically determines if the secret is static,
        dynamic, or rotated and calls the appropriate method to retrieve it. If silent_if_not_found is
        True, returns an empty string when the secret is not found. If json_attribute is provided,
        treats the secret as JSON and returns the specified attribute.
        """
        if not self.auto_guess_type:
            return self.get_static_secret(path, silent_if_not_found=silent_if_not_found, json_attribute=json_attribute)

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
                    )
                )
            case "rotated_secret":
                return str(self.get_rotated_secret(path, json_attribute=json_attribute, args=args))
            case "static_secret":
                return self.get_static_secret(
                    path, json_attribute=json_attribute, silent_if_not_found=silent_if_not_found
                )
            case _:
                raise ValueError(f"Unsupported secret type for auto-detection: '{secret.item_type}'")

    def get_static_secret(self, path: str, silent_if_not_found: bool = False, json_attribute: str | None = None) -> str:
        """
        Get a static secret from the given path.

        Checks permissions before retrieving the secret and raises PermissionsError if the user doesn't
        have read permission. If silent_if_not_found is True, returns an empty string when the secret
        is not found. If json_attribute is provided, treats the secret as JSON and returns the specified attribute.
        """
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
            return get_nested_attribute(res[path], json_attribute)  # type: ignore
        return str(res[path])

    def get_dynamic_secret(
        self, path: str, json_attribute: str | None = None, args: dict[str, Any] | None = None
    ) -> Any:
        """
        Get a dynamic secret from the given path.

        Dynamic secrets are generated on-demand, such as database credentials. Checks permissions
        before retrieving the secret and raises PermissionsError if the user doesn't have read
        permission. If json_attribute is provided, treats the result as JSON and returns the
        specified attribute.
        """
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
            return get_nested_attribute(res, json_attribute)
        return res

    def get_rotated_secret(
        self, path: str, json_attribute: str | None = None, args: dict[str, Any] | None = None
    ) -> Any:
        """
        Get a rotated secret from the given path.

        Rotated secrets are automatically replaced on a schedule. Checks permissions before
        retrieving the secret and raises PermissionsError if the user doesn't have read
        permission. If json_attribute is provided, treats the result as JSON and returns the
        specified attribute.
        """
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
            return get_nested_attribute(res, json_attribute)
        return res

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
        """
        if not "write" in self.describe_permissions(path):
            raise PermissionsError(f"You do not have permission the secret '{path}'")

        res = self.api.update_secret_val(
            self.akeyless.UpdateSecretVal(name=path, value=str(value), token=self._get_token())
        )

    def upsert(self, path: str, value: Any) -> None:
        """
        Create or update a secret.

        This method attempts to update an existing secret, and if that fails, it tries to create
        a new one. The value is converted to a string before storage.
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

    def _get_token(self) -> str:
        """
        Get an authentication token for Akeyless API calls.

        Returns a cached token if available and not expired (within 10 seconds), otherwise obtains
        a new one using the configured authentication method. Tokens are valid for about an hour,
        but we set the refresh time to 30 minutes to be safe.
        """
        # AKeyless tokens live for an hour
        if (
            hasattr(self, "_token_refresh")
            and hasattr(self, "_token")
            and (self._token_refresh - datetime.datetime.now()).total_seconds() > 10
        ):
            return self._token

        auth_method_name = f"auth_{self.access_type}"
        if not hasattr(self, auth_method_name):
            raise ValueError(f"Requested Akeyless authentication with unsupported auth method: '{self.access_type}'")

        self._token_refresh = datetime.datetime.now() + datetime.timedelta(hours=0.5)
        self._token = getattr(self, auth_method_name)()
        return self._token

    def auth_aws_iam(self):
        """
        Authenticate using AWS IAM.

        Uses the akeyless_cloud_id package to generate a cloud ID and authenticates with Akeyless
        using the configured access_id.
        """
        from akeyless_cloud_id import CloudId  # type: ignore

        res = self.api.auth(
            self.akeyless.Auth(access_id=self.access_id, access_type="aws_iam", cloud_id=CloudId().generate())
        )
        return res.token  # type: ignore

    def auth_saml(self):
        """
        Authenticate using SAML.

        Uses the akeyless CLI to generate credentials and then retrieves a token either directly
        from the credentials file or by making an API call to convert the credentials to a token.
        """
        import json
        import os
        from pathlib import Path

        os.system(f"akeyless list-items --profile {self.profile} --path /not/a/real/path > /dev/null 2>&1")
        home = str(Path.home())
        with open(f"{home}/.akeyless/.tmp_creds/{self.profile}-{self.access_id}", "r") as creds_file:
            credentials = creds_file.read()
            credentials_json = json.loads(credentials)
        if "token" in credentials_json:
            return credentials_json["token"]
        # and now we can turn that into a token
        response = self.requests.post(
            "https://rest.akeyless.io/",
            data={
                "cmd": "static-creds-auth",
                "access-id": self.access_id,
                "creds": credentials.strip(),
            },
        )
        return response.json()["token"]

    def auth_jwt(self):
        """
        Authenticate using JWT.

        Retrieves the JWT from the environment variable specified by jwt_env_key and authenticates
        with Akeyless. Raises ValueError if jwt_env_key is not specified.
        """
        if not self.jwt_env_key:
            raise ValueError(
                "To use AKeyless JWT Auth, "
                "you must specify the name of the ENV key to load the JWT from when configuring AKeyless"
            )
        res = self.api.auth(
            self.akeyless.Auth(access_id=self.access_id, access_type="jwt", jwt=self.environment.get(self.jwt_env_key))
        )
        return res.token  # type: ignore

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
