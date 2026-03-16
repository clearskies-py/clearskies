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

        # Mock auth to return token with creds containing expiry
        mock_creds = MagicMock(expiry=2000)
        self.mock_api.auth.return_value = MagicMock(token="test-token", creds=mock_creds)

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

    # --- SAML auth tests ---

    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_returns_cached_token_when_valid(self, mock_file):
        """Test SAML auth returns cached token from creds file when it's still valid."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        mock_creds = {"token": "valid-cached-token", "expiry": 2000}
        mock_file.return_value.read.return_value = json.dumps(mock_creds)

        result = akeyless.auth_saml()

        # Should return tuple of (token, expiry)
        self.assertIsInstance(result, tuple)
        token, expiry = result
        self.assertEqual(token, "valid-cached-token")
        self.assertEqual(expiry, 2000)
        # Should NOT call subprocess (no need to re-authenticate)
        self.mock_subprocess.run.assert_not_called()
        # Should NOT call static-creds-auth API
        self.mock_requests.post.assert_not_called()

    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_reauths_when_token_expired(self, mock_file, mock_remove):
        """Test SAML auth deletes creds and re-authenticates when token is expired."""
        akeyless = self._create_akeyless_saml(mock_timestamp=2000)

        # First read: expired token; second read (after list-items): fresh token
        expired_creds = json.dumps({"token": "expired-token", "expiry": 1500})
        fresh_creds = json.dumps({"token": "fresh-token", "expiry": 5600})
        mock_file.return_value.read.side_effect = [expired_creds, fresh_creds]

        result = akeyless.auth_saml()

        token, expiry = result
        self.assertEqual(token, "fresh-token")
        self.assertEqual(expiry, 5600)
        # Should have deleted the creds file
        mock_remove.assert_called_once()
        # Should have called subprocess.run for list-items
        self.mock_subprocess.run.assert_called_once()
        call_args = self.mock_subprocess.run.call_args[0][0]
        self.assertEqual(call_args[0:2], ["akeyless", "list-items"])

    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_reauths_when_token_expiring_soon(self, mock_file, mock_remove):
        """Test SAML auth re-authenticates when token expires within buffer (default 300s)."""
        # Token expires at 2000, current time 1800 → only 200s left < 300s buffer
        akeyless = self._create_akeyless_saml(mock_timestamp=1800)

        almost_expired = json.dumps({"token": "almost-expired-token", "expiry": 2000})
        fresh_creds = json.dumps({"token": "fresh-token", "expiry": 5400})
        mock_file.return_value.read.side_effect = [almost_expired, fresh_creds]

        result = akeyless.auth_saml()

        token, expiry = result
        self.assertEqual(token, "fresh-token")
        self.assertEqual(expiry, 5400)
        # Should have re-authenticated
        self.mock_subprocess.run.assert_called_once()

    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_handles_no_creds_file(self, mock_file, mock_remove):
        """Test SAML auth when no credentials file exists initially."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # First read: FileNotFoundError; second read (after list-items): fresh creds
        fresh_creds = json.dumps({"token": "fresh-token", "expiry": 4600})
        mock_file.return_value.read.side_effect = [FileNotFoundError("No such file"), fresh_creds]

        # os.remove also fails (no file to delete)
        mock_remove.side_effect = FileNotFoundError("No such file")

        result = akeyless.auth_saml()

        token, expiry = result
        self.assertEqual(token, "fresh-token")
        self.assertEqual(expiry, 4600)
        # Should have called list-items
        self.mock_subprocess.run.assert_called_once()

    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_uses_ttl_fallback_when_no_expiry(self, mock_file, mock_remove):
        """Test SAML auth falls back to auth_token_ttl when credentials file has no expiry."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # First read: no expiry field → treated as expired, falls through to re-auth
        # (no "expiry" key means we can't validate, so it falls through)
        no_expiry_creds = json.dumps({"token": "token-without-expiry"})
        fresh_creds = json.dumps({"token": "fresh-token-no-expiry"})
        mock_file.return_value.read.side_effect = [no_expiry_creds, fresh_creds]

        result = akeyless.auth_saml()

        token, expiry = result
        self.assertEqual(token, "fresh-token-no-expiry")
        # Expiry uses TTL fallback since no expiry in response
        self.assertEqual(expiry, 1000 + 3600)

    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_rest_api_fallback_for_raw_credentials(self, mock_file, mock_remove):
        """Test SAML auth uses REST API when creds file has no token field."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        # First read: fails (no file); second read: raw credentials without token
        raw_creds = json.dumps({"some_cred_field": "value"})
        mock_file.return_value.read.side_effect = [FileNotFoundError("No such file"), raw_creds]
        mock_remove.side_effect = FileNotFoundError("No such file")

        # Mock REST API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "api-token", "expiry": 5000}
        self.mock_requests.post.return_value = mock_response

        result = akeyless.auth_saml()

        token, expiry = result
        self.assertEqual(token, "api-token")
        self.assertEqual(expiry, 5000)
        # Should have called the REST API
        self.mock_requests.post.assert_called_once()
        call_args = self.mock_requests.post.call_args
        self.assertEqual(call_args[0][0], "https://rest.akeyless.io/")
        self.assertEqual(call_args[1]["data"]["cmd"], "static-creds-auth")

    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_auth_saml_rest_api_fallback_uses_ttl_when_no_expiry(self, mock_file, mock_remove):
        """Test SAML REST API fallback uses auth_token_ttl when response has no expiry."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        raw_creds = json.dumps({"some_cred_field": "value"})
        mock_file.return_value.read.side_effect = [FileNotFoundError("No such file"), raw_creds]
        mock_remove.side_effect = FileNotFoundError("No such file")

        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "api-token"}
        self.mock_requests.post.return_value = mock_response

        result = akeyless.auth_saml()

        token, expiry = result
        self.assertEqual(token, "api-token")
        self.assertEqual(expiry, 1000 + 3600)

    # --- _get_token tests ---

    def test_get_token_with_valid_cached_token(self):
        """Test that _get_token returns cached token if still valid."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        akeyless._token = "cached-token"
        akeyless._token_expiry = 2000

        token = akeyless._get_token()

        self.assertEqual(token, "cached-token")
        self.mock_requests.post.assert_not_called()

    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_token_with_expired_cached_token(self, mock_file, mock_remove):
        """Test that _get_token fetches new token if cached token is expired."""
        akeyless = self._create_akeyless_saml(mock_timestamp=2000)

        akeyless._token = "expired-cached-token"
        akeyless._token_expiry = 1500

        # auth_saml will first try to read creds file (expired), then delete + list-items + read fresh
        expired_creds = json.dumps({"token": "still-expired", "expiry": 1500})
        fresh_creds = json.dumps({"token": "valid-new-token", "expiry": 5600})
        mock_file.return_value.read.side_effect = [expired_creds, fresh_creds]

        token = akeyless._get_token()

        self.assertEqual(token, "valid-new-token")
        self.assertEqual(akeyless._token_expiry, 5600)

    def test_get_token_refreshes_near_expiry(self):
        """Test that _get_token refreshes token when near expiry (within token_refresh_buffer)."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1995)

        akeyless._token = "almost-expired-token"
        akeyless._token_expiry = 2000

        with patch.object(akeyless, "auth_saml", return_value=("refreshed-token", 2500)):
            token = akeyless._get_token()

        self.assertEqual(token, "refreshed-token")
        self.assertEqual(akeyless._token_expiry, 2500)

    def test_get_token_always_expects_tuple(self):
        """Test that _get_token directly destructures the tuple from auth methods."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        with patch.object(akeyless, "auth_saml", return_value=("new-token", 5000)):
            token = akeyless._get_token()

        self.assertEqual(token, "new-token")
        self.assertEqual(akeyless._token_expiry, 5000)

    def test_get_token_raises_on_non_tuple_return(self):
        """Test that _get_token raises when auth method doesn't return tuple (contract violation)."""
        akeyless = self._create_akeyless_saml(mock_timestamp=1000)

        with patch.object(akeyless, "auth_saml", return_value="just-a-string"):
            with self.assertRaises((TypeError, ValueError)):
                akeyless._get_token()

    # --- AWS IAM and JWT auth tests ---

    def test_auth_aws_iam_returns_tuple(self):
        """Test that auth_aws_iam returns a (token, expiry) tuple from the API response."""
        akeyless = self._create_akeyless_aws_iam(mock_timestamp=1000)

        mock_creds = MagicMock(expiry=5000)
        self.mock_api.auth.return_value = MagicMock(token="aws-token", creds=mock_creds)

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

        mock_env = MagicMock()
        mock_env.get.return_value = "my-jwt-value"
        akeyless.environment = mock_env

        mock_creds = MagicMock(expiry=6000)
        self.mock_api.auth.return_value = MagicMock(token="jwt-token", creds=mock_creds)

        result = akeyless.auth_jwt()

        self.assertIsInstance(result, tuple)
        token, expiry = result
        self.assertEqual(token, "jwt-token")
        self.assertEqual(expiry, 6000.0)

    def test_auth_aws_iam_falls_back_to_ttl_when_creds_is_none(self):
        """Test that auth_aws_iam uses auth_token_ttl when creds is None (no expiry available)."""
        akeyless = self._create_akeyless_aws_iam(mock_timestamp=1000)

        # Simulate AuthOutput with creds=None (as returned by the real Akeyless SDK)
        self.mock_api.auth.return_value = MagicMock(token="aws-token", creds=None)

        with patch.dict("sys.modules", {"akeyless_cloud_id": MagicMock()}):
            import akeyless_cloud_id  # type: ignore

            akeyless_cloud_id.CloudId.return_value.generate.return_value = "mock-cloud-id"
            result = akeyless.auth_aws_iam()

        token, expiry = result
        self.assertEqual(token, "aws-token")
        # Should fall back to now + auth_token_ttl (1000 + 3600)
        self.assertEqual(expiry, 1000 + 3600)

    def test_auth_aws_iam_handles_creds_expiry_zero(self):
        """Test that auth_aws_iam correctly returns expiry=0 when creds.expiry is 0 (epoch)."""
        akeyless = self._create_akeyless_aws_iam(mock_timestamp=1000)

        # expiry=0 is falsy but should still be used (not fall back to TTL)
        mock_creds = MagicMock(expiry=0)
        self.mock_api.auth.return_value = MagicMock(token="aws-token", creds=mock_creds)

        with patch.dict("sys.modules", {"akeyless_cloud_id": MagicMock()}):
            import akeyless_cloud_id  # type: ignore

            akeyless_cloud_id.CloudId.return_value.generate.return_value = "mock-cloud-id"
            result = akeyless.auth_aws_iam()

        token, expiry = result
        self.assertEqual(token, "aws-token")
        # Should return 0.0 (from creds.expiry), NOT the TTL fallback
        self.assertEqual(expiry, 0.0)

    def test_auth_jwt_falls_back_to_ttl_when_creds_is_none(self):
        """Test that auth_jwt uses auth_token_ttl when creds is None (no expiry available)."""
        akeyless = self._create_akeyless_jwt(mock_timestamp=1000)

        mock_env = MagicMock()
        mock_env.get.return_value = "my-jwt-value"
        akeyless.environment = mock_env

        # Simulate AuthOutput with creds=None
        self.mock_api.auth.return_value = MagicMock(token="jwt-token", creds=None)

        result = akeyless.auth_jwt()

        token, expiry = result
        self.assertEqual(token, "jwt-token")
        # Should fall back to now + auth_token_ttl (1000 + 3600)
        self.assertEqual(expiry, 1000 + 3600)

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


if __name__ == "__main__":
    unittest.main()
