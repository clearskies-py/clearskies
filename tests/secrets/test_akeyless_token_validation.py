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

    def test_is_token_valid_with_valid_token(self):
        """Test that _is_token_valid returns True for a valid token."""
        akeyless = self._create_akeyless_saml()

        # Mock successful API call
        self.mock_api.describe_permissions.return_value = MagicMock(client_permissions=["read"])

        result = akeyless._is_token_valid("valid-token")

        self.assertTrue(result)
        self.mock_api.describe_permissions.assert_called_once()

    def test_is_token_valid_with_expired_token(self):
        """Test that _is_token_valid returns False for an expired token."""
        akeyless = self._create_akeyless_saml()

        # Mock API call that raises an exception (expired token)
        self.mock_api.describe_permissions.side_effect = Exception("Token expired")

        result = akeyless._is_token_valid("expired-token")

        self.assertFalse(result)
        self.mock_api.describe_permissions.assert_called_once()

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

    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_expired_token_by_expiry(self, mock_file, mock_os_system):
        """Test SAML auth when credentials file has an expired token (by expiry timestamp)."""
        # Mock current time as 2000 and expiry as 1500 (token is expired)
        akeyless = self._create_akeyless_saml(mock_timestamp=2000)

        mock_creds = {"token": "expired-token", "expiry": 1500}
        mock_file.return_value.read.return_value = json.dumps(mock_creds)

        # Mock the static-creds-auth response with token and expiry
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "new-fresh-token", "expiry": 2500}
        self.mock_requests.post.return_value = mock_response

        result = akeyless.auth_saml()

        # Should call static-creds-auth to get a new token
        self.mock_requests.post.assert_called_once()
        # Should return tuple of (token, expiry)
        token, expiry = result
        self.assertEqual(token, "new-fresh-token")
        self.assertEqual(expiry, 2500)
        # Should NOT validate via API (expiry check is sufficient)
        self.mock_api.describe_permissions.assert_not_called()

    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_token_expiring_soon(self, mock_file, mock_os_system):
        """Test SAML auth when token is expiring within 10 seconds."""
        # Mock current time as 1995 and expiry as 2000 (token expires in 5 seconds)
        akeyless = self._create_akeyless_saml(mock_timestamp=1995)

        mock_creds = {"token": "almost-expired-token", "expiry": 2000}
        mock_file.return_value.read.return_value = json.dumps(mock_creds)

        # Mock the static-creds-auth response with token and expiry
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "new-fresh-token", "expiry": 2500}
        self.mock_requests.post.return_value = mock_response

        result = akeyless.auth_saml()

        # Should get a new token (within 10 second buffer)
        self.mock_requests.post.assert_called_once()
        token, expiry = result
        self.assertEqual(token, "new-fresh-token")
        self.assertEqual(expiry, 2500)

    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_valid_token_no_expiry_field(self, mock_file, mock_os_system):
        """Test SAML auth when credentials file has a token but no expiry field (fallback to API validation)."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # Mock credentials file with a valid token but no expiry field (backward compatibility)
        mock_creds = {"token": "valid-cached-token"}
        mock_file.return_value.read.return_value = json.dumps(mock_creds)

        # Mock token validation to return True
        self.mock_api.describe_permissions.return_value = MagicMock(client_permissions=["read"])

        result = akeyless.auth_saml()

        # Should return tuple with fallback expiry (30 minutes)
        token, expiry = result
        self.assertEqual(token, "valid-cached-token")
        self.assertEqual(expiry, 1000 + 1800)  # 30 minutes = 1800 seconds
        # Should NOT call static-creds-auth API
        self.mock_requests.post.assert_not_called()
        # Should have validated the token via API (fallback when no expiry)
        self.mock_api.describe_permissions.assert_called()

    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_with_expired_token_no_expiry_field(self, mock_file, mock_os_system):
        """Test SAML auth when credentials file has an expired token and no expiry field."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # Mock credentials file with an expired token and no expiry field
        mock_creds = {"token": "expired-token"}
        mock_file.return_value.read.return_value = json.dumps(mock_creds)

        # Mock token validation to return False (expired)
        self.mock_api.describe_permissions.side_effect = Exception("Token expired")

        # Mock the static-creds-auth response with token and fallback expiry
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "new-fresh-token"}  # No expiry in response
        self.mock_requests.post.return_value = mock_response

        result = akeyless.auth_saml()

        # Should call static-creds-auth to get a new token
        self.mock_requests.post.assert_called_once()
        # Should return tuple with fallback expiry
        token, expiry = result
        self.assertEqual(token, "new-fresh-token")
        self.assertEqual(expiry, 1000 + 1800)  # Fallback: 30 minutes

    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_without_token_in_credentials(self, mock_file, mock_os_system):
        """Test SAML auth when credentials file doesn't have a token field."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # Mock credentials file without a token field
        mock_creds = {"some_other_field": "value"}
        mock_file.return_value.read.return_value = json.dumps(mock_creds)

        # Mock the static-creds-auth response
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "new-token", "expiry": 2500}
        self.mock_requests.post.return_value = mock_response

        result = akeyless.auth_saml()

        # Should call static-creds-auth to get a token
        self.mock_requests.post.assert_called_once()
        # Should return tuple
        token, expiry = result
        self.assertEqual(token, "new-token")
        self.assertEqual(expiry, 2500)

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

    @patch("os.system")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_token_with_expired_cached_token(self, mock_file, mock_os_system):
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
        # Should have called auth method
        mock_os_system.assert_called()

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
