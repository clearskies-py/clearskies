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

        # Mock the now property if timestamp provided
        if mock_timestamp is not None:
            mock_dt = Mock(spec=datetime.datetime)
            mock_dt.timestamp.return_value = mock_timestamp
            akeyless.now = mock_dt

        return akeyless

    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_valid_token_and_expiry(self, mock_file, mock_os_system):
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

    @patch("os.path.exists")
    @patch("subprocess.run")
    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_expired_token_by_expiry(self, mock_file, mock_os_system, mock_subprocess, mock_exists):
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
        mock_subprocess.return_value = mock_subprocess_result

        result = akeyless.auth_saml()

        # Should have called subprocess.run for auth command
        self.assertEqual(mock_subprocess.call_count, 1)
        # Check that the auth command was called with correct parameters
        auth_call_args = mock_subprocess.call_args[0][0]
        self.assertEqual(
            auth_call_args, ["akeyless", "auth", "--access-id", "p-test123", "--access-type", "saml", "--json"]
        )

        # Should return tuple of (token, expiry)
        token, expiry = result
        self.assertEqual(token, "new-fresh-token")
        # Expiry should be current time + auth_token_ttl (3600 by default)
        self.assertEqual(expiry, 2000 + 3600)

    @patch("os.path.exists")
    @patch("subprocess.run")
    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_token_expiring_soon(self, mock_file, mock_os_system, mock_subprocess, mock_exists):
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
        mock_subprocess.return_value = mock_subprocess_result

        result = akeyless.auth_saml()

        # Should get a new token (within the refresh buffer)
        self.assertEqual(mock_subprocess.call_count, 1)
        token, expiry = result
        self.assertEqual(token, "new-fresh-token")
        self.assertEqual(expiry, 1800 + 3600)

    @patch("os.path.exists")
    @patch("subprocess.run")
    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_without_token_in_credentials(self, mock_file, mock_os_system, mock_subprocess, mock_exists):
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
        mock_subprocess.return_value = mock_subprocess_result

        result = akeyless.auth_saml()

        # Should have called akeyless CLI auth command
        self.assertEqual(mock_subprocess.call_count, 1)
        # Should return tuple
        token, expiry = result
        self.assertEqual(token, "new-token")
        self.assertEqual(expiry, 1000 + 3600)

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
        """Test that _get_token refreshes token when near expiry (< 10 seconds)."""
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


if __name__ == "__main__":
    unittest.main()
