import datetime
import json
import unittest
from unittest.mock import MagicMock, Mock, mock_open, patch

from clearskies.di import Di
from clearskies.secrets.akeyless import Akeyless


class AkeylessTokenValidationTest(unittest.TestCase):
    """Tests for Akeyless token validation functionality."""

    def setUp(self):
        self.mock_api = MagicMock()
        self.mock_akeyless_module = MagicMock()
        self.mock_akeyless_module.Configuration.return_value = MagicMock()
        self.mock_akeyless_module.ApiClient.return_value = MagicMock()
        self.mock_akeyless_module.V2Api.return_value = self.mock_api

        # Mock describe_permissions to return a successful response by default
        self.mock_api.describe_permissions.return_value = MagicMock(client_permissions=["read", "write", "list"])

        # Mock auth to return token and expiry
        self.mock_api.auth.return_value = MagicMock(token="test-token", expiry=2000)

        # Create DI container with mocked akeyless module
        self.di = Di(bindings={"akeyless_sdk": self.mock_akeyless_module})

        # Mock requests for SAML auth
        self.mock_requests = MagicMock()

        # Mock subprocess for DI injection
        self.mock_subprocess = MagicMock()

    def _create_akeyless_saml(self, mock_timestamp=None):
        """Create an Akeyless SAML instance with mocked dependencies."""
        akeyless = Akeyless(
            access_id="p-test123",
            access_type="saml",
            profile="default",
        )
        # Initialize injectable properties with DI
        akeyless.injectable_properties(self.di)
        akeyless._api = self.mock_api
        akeyless.requests = self.mock_requests
        akeyless.subprocess = self.mock_subprocess

        # Mock the now property if timestamp provided
        if mock_timestamp is not None:
            mock_dt = Mock(spec=datetime.datetime)
            mock_dt.timestamp.return_value = mock_timestamp
            akeyless.now = mock_dt

        return akeyless

    def _create_akeyless_aws_iam(self, mock_timestamp=None):
        """Create an Akeyless AWS IAM instance with mocked dependencies."""
        akeyless = Akeyless(
            access_id="p-test123",
            access_type="aws_iam",
        )
        akeyless.injectable_properties(self.di)
        akeyless._api = self.mock_api
        akeyless.subprocess = self.mock_subprocess

        if mock_timestamp is not None:
            mock_dt = Mock(spec=datetime.datetime)
            mock_dt.timestamp.return_value = mock_timestamp
            akeyless.now = mock_dt

        return akeyless

    def _create_akeyless_jwt(self, mock_timestamp=None):
        """Create an Akeyless JWT instance with mocked dependencies."""
        akeyless = Akeyless(
            access_id="p-test123",
            access_type="jwt",
            jwt_env_key="MY_JWT",
        )
        akeyless.injectable_properties(self.di)
        akeyless._api = self.mock_api
        akeyless.subprocess = self.mock_subprocess

        if mock_timestamp is not None:
            mock_dt = Mock(spec=datetime.datetime)
            mock_dt.timestamp.return_value = mock_timestamp
            akeyless.now = mock_dt

        return akeyless

    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_valid_token_and_expiry(self, mock_file):
        """Test SAML auth when credentials file has a valid token with expiry."""
        # Mock current time as 1000 and expiry as 2000 (token is valid)
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        mock_creds = {"token": "valid-cached-token", "expiry": 2000}
        mock_file.return_value.read.return_value = json.dumps(mock_creds)

        result = akeyless.auth_saml()

        # Should return tuple of (token, expiry)
        self.assertIsInstance(result, tuple)
        token, expiry = result
        self.assertEqual(token, "valid-cached-token")
        self.assertEqual(expiry, 2000)
        # Should NOT call static-creds-auth API
        self.mock_requests.post.assert_not_called()
        # Should NOT validate the token via API (expiry check is sufficient)
        self.mock_api.describe_permissions.assert_not_called()
        # Should NOT have called subprocess
        self.mock_subprocess.run.assert_not_called()

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_expired_token_by_expiry(self, mock_file, mock_exists):
        """Test SAML auth when credentials file has an expired token (by expiry timestamp)."""
        # Mock current time as 2000 and expiry as 1500 (token is expired)
        akeyless = self._create_akeyless_saml(mock_timestamp=2000)

        # Mock that creds file exists
        mock_exists.return_value = True

        # First call: read expired token
        mock_file.return_value.read.return_value = json.dumps({"token": "expired-token", "expiry": 1500})

        # Mock subprocess.run to return a successful auth response
        mock_subprocess_result = Mock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = json.dumps({"token": "new-fresh-token"})
        self.mock_subprocess.run.return_value = mock_subprocess_result

        result = akeyless.auth_saml()

        # Should have called subprocess.run for auth command
        self.assertEqual(self.mock_subprocess.run.call_count, 1)
        # Check that the auth command was called with correct parameters including --profile
        auth_call_args = self.mock_subprocess.run.call_args[0][0]
        self.assertEqual(
            auth_call_args,
            ["akeyless", "auth", "--access-id", "p-test123", "--access-type", "saml", "--profile", "default", "--json"],
        )

        # Should return tuple of (token, expiry)
        token, expiry = result
        self.assertEqual(token, "new-fresh-token")
        # Expiry should be current time + auth_token_ttl (3600 by default) since response didn't include expiry
        self.assertEqual(expiry, 2000 + 3600)

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_token_expiring_soon(self, mock_file, mock_exists):
        """Test SAML auth when token is expiring within the refresh buffer (default 5 minutes/300 seconds)."""
        # Mock current time as 1800 and expiry as 2000 (token expires in 200 seconds, less than 300 second buffer)
        akeyless = self._create_akeyless_saml(mock_timestamp=1800)

        # Mock that creds file exists
        mock_exists.return_value = True

        # Read almost expired token
        mock_file.return_value.read.return_value = json.dumps({"token": "almost-expired-token", "expiry": 2000})

        # Mock subprocess.run to return a successful auth response
        mock_subprocess_result = Mock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = json.dumps({"token": "new-fresh-token"})
        self.mock_subprocess.run.return_value = mock_subprocess_result

        result = akeyless.auth_saml()

        # Should get a new token (within the refresh buffer)
        self.assertEqual(self.mock_subprocess.run.call_count, 1)
        token, expiry = result
        self.assertEqual(token, "new-fresh-token")
        self.assertEqual(expiry, 1800 + 3600)

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_without_token_in_credentials(self, mock_file, mock_exists):
        """Test SAML auth when credentials file doesn't have a token field."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # Mock that creds file exists
        mock_exists.return_value = True

        # Read credentials without token
        mock_file.return_value.read.return_value = json.dumps({"some_other_field": "value"})

        # Mock subprocess.run to return a successful auth response
        mock_subprocess_result = Mock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = json.dumps({"token": "new-token"})
        self.mock_subprocess.run.return_value = mock_subprocess_result

        result = akeyless.auth_saml()

        # Should have called akeyless CLI auth command via DI-injected subprocess
        self.assertEqual(self.mock_subprocess.run.call_count, 1)
        # Should return tuple
        token, expiry = result
        self.assertEqual(token, "new-token")
        self.assertEqual(expiry, 1000 + 3600)

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_uses_expiry_from_cli_response(self, mock_file, mock_exists):
        """Test SAML auth uses expiry from CLI JSON response when available."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # Mock that creds file exists
        mock_exists.return_value = True

        # Read credentials without token
        mock_file.return_value.read.return_value = json.dumps({"some_other_field": "value"})

        # Mock subprocess.run to return a response WITH expiry
        mock_subprocess_result = Mock()
        mock_subprocess_result.returncode = 0
        mock_subprocess_result.stdout = json.dumps({"token": "new-token", "expiry": 5000})
        self.mock_subprocess.run.return_value = mock_subprocess_result

        result = akeyless.auth_saml()

        token, expiry = result
        self.assertEqual(token, "new-token")
        # Should use the expiry from the response, not the fallback TTL
        self.assertEqual(expiry, 5000)

    def test_get_token_with_valid_cached_token(self):
        """Test that _get_token returns cached token if still valid."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # Set up a valid cached token with expiry in the future
        akeyless._token = "cached-token"
        akeyless._token_expiry = 2000  # Expires at 2000, current time is 1000

        token = akeyless._get_token()

        # Should return the cached token
        self.assertEqual(token, "cached-token")
        # Should NOT call auth method
        self.mock_requests.post.assert_not_called()

    @patch("builtins.open", new_callable=mock_open)
    def test_get_token_with_expired_cached_token(self, mock_file):
        """Test that _get_token fetches new token if cached token is expired."""
        akeyless = self._create_akeyless_saml(mock_timestamp=2000)

        # Set up an expired cached token
        akeyless._token = "expired-cached-token"
        akeyless._token_expiry = 1500  # Expired (current time is 2000)

        # Mock credentials file
        mock_creds = {"token": "valid-new-token", "expiry": 2500}
        mock_file.return_value.read.return_value = json.dumps(mock_creds)

        token = akeyless._get_token()

        # Should return a new token
        self.assertEqual(token, "valid-new-token")
        # Token expiry should be updated
        self.assertEqual(akeyless._token_expiry, 2500)

    def test_get_token_refreshes_near_expiry(self):
        """Test that _get_token refreshes token when near expiry (within token_refresh_buffer)."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1995)

        # Set up a token that expires in 5 seconds (at 2000, current time is 1995)
        akeyless._token = "almost-expired-token"
        akeyless._token_expiry = 2000

        # Mock the auth method to return tuple
        with patch.object(akeyless, "auth_saml", return_value=("refreshed-token", 2500)):
            token = akeyless._get_token()

        # Should fetch a new token
        self.assertEqual(token, "refreshed-token")
        # Should have updated the expiry
        self.assertEqual(akeyless._token_expiry, 2500)

    def test_auth_aws_iam_returns_tuple(self):
        """Test that auth_aws_iam returns a (token, expiry) tuple from the API response."""
        akeyless = self._create_akeyless_aws_iam(mock_timestamp=1000)

        # Mock the CloudId import and API auth response
        self.mock_api.auth.return_value = MagicMock(token="aws-token", expiry=5000.0)

        with patch.dict("sys.modules", {"akeyless_cloud_id": MagicMock()}):
            import akeyless_cloud_id  # type: ignore

            akeyless_cloud_id.CloudId.return_value.generate.return_value = "mock-cloud-id"
            result = akeyless.auth_aws_iam()

        self.assertIsInstance(result, tuple)
        token, expiry = result
        self.assertEqual(token, "aws-token")
        self.assertEqual(expiry, 5000.0)

    def test_auth_jwt_returns_tuple(self):
        """Test that auth_jwt returns a (token, expiry) tuple from the API response."""
        akeyless = self._create_akeyless_jwt(mock_timestamp=1000)

        # Mock environment to return JWT
        mock_env = MagicMock()
        mock_env.get.return_value = "my-jwt-value"
        akeyless.environment = mock_env

        # Mock API auth response
        self.mock_api.auth.return_value = MagicMock(token="jwt-token", expiry=6000.0)

        result = akeyless.auth_jwt()

        self.assertIsInstance(result, tuple)
        token, expiry = result
        self.assertEqual(token, "jwt-token")
        self.assertEqual(expiry, 6000.0)

    def test_auth_jwt_raises_without_jwt_env_key(self):
        """Test that auth_jwt raises ValueError when jwt_env_key is not provided."""
        akeyless = Akeyless(
            access_id="p-test123",
            access_type="jwt",
        )
        akeyless.injectable_properties(self.di)
        akeyless._api = self.mock_api

        with self.assertRaises(ValueError):
            akeyless.auth_jwt()

    def test_get_token_handles_legacy_string_return(self):
        """Test that _get_token handles auth methods that return a string instead of tuple."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # Mock the auth method to return just a string (legacy behavior)
        with patch.object(akeyless, "auth_saml", return_value="legacy-token"):
            token = akeyless._get_token()

        self.assertEqual(token, "legacy-token")
        # Should have set expiry using fallback TTL
        self.assertEqual(akeyless._token_expiry, 1000 + 3600)

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_cli_failure_raises_runtime_error(self, mock_file, mock_exists):
        """Test SAML auth raises RuntimeError when akeyless CLI auth command fails."""
        akeyless = self._create_akeyless_saml(mock_timestamp=2000)

        # Mock that creds file exists with expired token
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({"token": "expired-token", "expiry": 1500})

        # Mock subprocess.run to return a failure
        mock_subprocess_result = Mock()
        mock_subprocess_result.returncode = 1
        mock_subprocess_result.stderr = "SAML authentication timed out"
        self.mock_subprocess.run.return_value = mock_subprocess_result

        with self.assertRaises(RuntimeError) as context:
            akeyless.auth_saml()

        self.assertIn("SAML authentication failed", str(context.exception))
        self.assertIn("SAML authentication timed out", str(context.exception))

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_cli_failure_with_empty_stderr(self, mock_file, mock_exists):
        """Test SAML auth raises RuntimeError even when stderr is empty."""
        akeyless = self._create_akeyless_saml(mock_timestamp=2000)

        # Mock that creds file exists with expired token
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({"token": "expired-token", "expiry": 1500})

        # Mock subprocess.run to return a failure with empty stderr
        mock_subprocess_result = Mock()
        mock_subprocess_result.returncode = 127  # command not found
        mock_subprocess_result.stderr = ""
        self.mock_subprocess.run.return_value = mock_subprocess_result

        with self.assertRaises(RuntimeError) as context:
            akeyless.auth_saml()

        self.assertIn("SAML authentication failed", str(context.exception))

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_auth_saml_no_creds_file_uses_list_items_fallback(self, mock_file, mock_exists):
        """Test SAML auth tries list-items when no credentials file exists, then falls back to auth."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # First call to _read_saml_credentials: FileNotFoundError (no creds file)
        # After list-items: still FileNotFoundError (list-items didn't create the file)
        mock_file.side_effect = FileNotFoundError("No such file")

        # Mock os.path.exists: creds file does NOT exist
        mock_exists.return_value = False

        # Mock subprocess.run for both calls:
        # 1st call: list-items (doesn't create creds file)
        # 2nd call: akeyless auth (returns token)
        list_items_result = Mock()
        list_items_result.returncode = 0
        list_items_result.stdout = ""

        auth_result = Mock()
        auth_result.returncode = 0
        auth_result.stdout = json.dumps({"token": "fallback-token", "expiry": 5000})

        self.mock_subprocess.run.side_effect = [list_items_result, auth_result]

        result = akeyless.auth_saml()

        # Should have called subprocess.run twice: list-items then auth
        self.assertEqual(self.mock_subprocess.run.call_count, 2)

        # First call should be list-items
        first_call_args = self.mock_subprocess.run.call_args_list[0][0][0]
        self.assertEqual(first_call_args[0:2], ["akeyless", "list-items"])

        # Second call should be auth
        second_call_args = self.mock_subprocess.run.call_args_list[1][0][0]
        self.assertEqual(second_call_args[0:2], ["akeyless", "auth"])

        # Should return the token from auth command
        token, expiry = result
        self.assertEqual(token, "fallback-token")
        self.assertEqual(expiry, 5000)

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_list_items_creates_valid_creds(self, mock_file, mock_exists):
        """Test SAML auth succeeds when list-items creates valid credentials file."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # os.path.exists: creds file does NOT exist initially
        mock_exists.return_value = False

        # First _read_saml_credentials call: FileNotFoundError
        # Second _read_saml_credentials call (after list-items): valid creds
        valid_creds = json.dumps({"token": "list-items-token", "expiry": 5000})
        mock_file.side_effect = [
            FileNotFoundError("No such file"),
            mock_open(read_data=valid_creds)(),
        ]

        # Mock subprocess.run for list-items
        list_items_result = Mock()
        list_items_result.returncode = 0
        self.mock_subprocess.run.return_value = list_items_result

        result = akeyless.auth_saml()

        # Should have called subprocess.run once (list-items only, since it created valid creds)
        self.assertEqual(self.mock_subprocess.run.call_count, 1)

        # Should return the token from the credentials file
        token, expiry = result
        self.assertEqual(token, "list-items-token")
        self.assertEqual(expiry, 5000)


if __name__ == "__main__":
    unittest.main()
