import json
import unittest
from types import SimpleNamespace

import clearskies
from clearskies.di.di import Di


class SecretBearerTest(unittest.TestCase):
    def test_overview(self):
        def get_environment(key):
            if key == "MY_AUTH_SECRET":
                return "SUPERSECRET"
            raise KeyError("Oops")

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "world"},
                authentication=clearskies.authentication.SecretBearer(environment_key="MY_AUTH_SECRET"),
            ),
            bindings={
                "environment": SimpleNamespace(get=get_environment),
            },
        )
        status_code, response_data, response_headers = context(request_headers={"Authorization": "SUPERSECRET"})
        print(response_data)
        assert status_code == 200

        status_code, response_data, response_headers = context(request_headers={"Authorization": "supersecret"})
        assert status_code == 401

    def test_secret_key(self):
        def fetch_secret(path, refresh=False, **kwargs):
            if path == "/path/to/my/secret":
                return "SUPERSECRET"
            raise KeyError(f"Attempt to fetch non-existent secret: {path}")

        fake_secret_manager = SimpleNamespace(get=fetch_secret)

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "world"},
                authentication=clearskies.authentication.SecretBearer(secret_key="/path/to/my/secret"),
            ),
            bindings={
                "secrets": fake_secret_manager,
            },
        )
        status_code, response_data, response_headers = context(request_headers={"Authorization": "SUPERSECRET"})
        assert status_code == 200

        status_code, response_data, response_headers = context(request_headers={"Authorization": "supersecret"})
        assert status_code == 401

    def test_alternate_secret_key(self):
        def fetch_secret(path, refresh=False, **kwargs):
            if path == "/path/to/my/secret":
                return "SUPERSECRET"
            if path == "/path/to/alternate/secret":
                return "ALSOOKAY"
            raise KeyError(f"Attempt to fetch non-existent secret: {path}")

        fake_secret_manager = SimpleNamespace(get=fetch_secret)

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "world"},
                authentication=clearskies.authentication.SecretBearer(
                    secret_key="/path/to/my/secret",
                    alternate_secret_key="/path/to/alternate/secret",
                ),
            ),
            bindings={
                "secrets": fake_secret_manager,
            },
        )
        status_code, response_data, response_headers = context(request_headers={"Authorization": "SUPERSECRET"})
        assert status_code == 200

        status_code, response_data, response_headers = context(request_headers={"Authorization": "ALSOOKAY"})
        assert status_code == 200

        status_code, response_data, response_headers = context(request_headers={"Authorization": "supersecret"})
        assert status_code == 401

    def test_alternate_environment_key(self):
        def get_environment(key):
            if key == "MY_AUTH_SECRET":
                return "SUPERSECRET"
            if key == "MY_ALT_SECRET":
                return "ALSOOKAY"
            raise KeyError("Oops")

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "world"},
                authentication=clearskies.authentication.SecretBearer(
                    environment_key="MY_AUTH_SECRET",
                    alternate_environment_key="MY_ALT_SECRET",
                ),
            ),
            bindings={
                "environment": SimpleNamespace(get=get_environment),
            },
        )
        status_code, response_data, response_headers = context(request_headers={"Authorization": "SUPERSECRET"})
        assert status_code == 200

        status_code, response_data, response_headers = context(request_headers={"Authorization": "ALSOOKAY"})
        assert status_code == 200

        status_code, response_data, response_headers = context(request_headers={"Authorization": "supersecret"})
        assert status_code == 401

    def test_header_prefix(self):
        def get_environment(key):
            if key == "MY_AUTH_SECRET":
                return "SUPERSECRET"
            raise KeyError("Oops")

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "world"},
                authentication=clearskies.authentication.SecretBearer(
                    environment_key="MY_AUTH_SECRET", header_prefix="secret-token "
                ),
            ),
            bindings={
                "environment": SimpleNamespace(get=get_environment),
            },
        )
        status_code, response_data, response_headers = context(
            request_headers={"Authorization": "SECRET-TOKEN SUPERSECRET"}
        )
        assert status_code == 200

        status_code, response_data, response_headers = context(
            request_headers={"Authorization": "SECRET_TOKENSUPERSECRET"}
        )
        assert status_code == 401

        status_code, response_data, response_headers = context(request_headers={"Authorization": "SUPERSECRET"})
        assert status_code == 401

    def test_retry_auth_forces_secret_refresh_when_using_secret_manager(self):
        calls = []

        def fetch_secret(path, refresh=False, **kwargs):
            calls.append((path, refresh))
            if path == "/path/to/my/secret":
                return "NEWSECRET" if refresh else "OLDSECRET"
            raise KeyError(f"Attempt to fetch non-existent secret: {path}")

        bearer = clearskies.authentication.SecretBearer(secret_key="/path/to/my/secret")
        di = Di(bindings={"secrets": SimpleNamespace(get=fetch_secret)})
        bearer.injectable_properties(di)

        self.assertEqual({"Authorization": "OLDSECRET"}, bearer.headers())
        self.assertEqual({"Authorization": "NEWSECRET"}, bearer.headers(retry_auth=True))
        self.assertEqual(
            [
                ("/path/to/my/secret", False),
                ("/path/to/my/secret", True),
            ],
            calls,
        )

    def test_refresh_parameter_forces_secret_refresh(self):
        calls = []

        def fetch_secret(path, refresh=False, **kwargs):
            calls.append((path, refresh))
            return "FRESH_SECRET" if refresh else "OLD_SECRET"

        bearer = clearskies.authentication.SecretBearer(
            secret_key="/path/to/secret",
            refresh=True,  # Forces refresh on every access
        )
        di = Di(bindings={"secrets": SimpleNamespace(get=fetch_secret)})
        bearer.injectable_properties(di)

        # First access gets "FRESH_SECRET" due to refresh=True
        headers = bearer.headers()
        self.assertIn("FRESH_SECRET", headers["Authorization"])
        # Verify it calls with refresh=True
        self.assertEqual([("/path/to/secret", True)], calls)

    def test_json_path_extracts_string_value(self):
        calls = []

        def fetch_secret(path, refresh=False, json_path=None, **kwargs):
            calls.append((path, refresh, json_path))
            mock_creds = {"db_password": "my_strong_password", "db_host": "localhost", "api_key": "sk_live_12345"}

            if json_path == "db_password":
                return "my_strong_password"
            elif json_path and json_path.startswith("credentials."):
                # Handle nested paths like "credentials.api_key"
                parts = json_path.split(".")
                if len(parts) == 2 and parts[0] == "credentials":
                    attr_name = parts[1]
                    if attr_name in mock_creds["credentials"]:
                        return mock_creds["credentials"][attr_name]
            elif json_path:
                return mock_creds.get(json_path, "default")
            return json.dumps(mock_creds)

        bearer = clearskies.authentication.SecretBearer(secret_key="/path/to/creds", json_path="db_password")

        di = Di(bindings={"secrets": SimpleNamespace(get=fetch_secret)})
        bearer.injectable_properties(di)

        headers = bearer.headers()
        # Should return just the extracted password, not JSON
        self.assertIn("my_strong_password", headers["Authorization"])

        # Verify it was called with json_path parameter
        self.assertEqual(1, len(calls))
        self.assertEqual("/path/to/creds", calls[0][0])
        self.assertEqual(False, calls[0][1])
        self.assertEqual("db_password", calls[0][2])

    def test_json_path_with_nested_path(self):
        calls = []

        def fetch_secret(path, refresh=False, json_path=None, **kwargs):
            calls.append((path, refresh, json_path))
            mock_creds = {"credentials": {"api_key": "sk_live_12345", "secret_token": "super_secret_67890"}}

            if json_path == "credentials.api_key":
                return "sk_live_12345"
            elif json_path == "credentials.secret_token":
                return "super_secret_67890"
            elif json_path and "." in json_path:
                # Handle nested paths like "credentials.api_key"
                parts = json_path.split(".")
                if len(parts) == 2:
                    parent, child = parts
                    if parent == "credentials" and child in mock_creds.get(parent, {}):
                        return mock_creds[parent][child]
            return json.dumps(mock_creds)

        bearer = clearskies.authentication.SecretBearer(
            secret_key="/path/to/nested/creds", json_path="credentials.api_key"
        )

        di = Di(bindings={"secrets": SimpleNamespace(get=fetch_secret)})
        bearer.injectable_properties(di)

        headers = bearer.headers()
        self.assertIn("sk_live_12345", headers["Authorization"])

        self.assertEqual(1, len(calls))
        self.assertEqual("/path/to/nested/creds", calls[0][0])
        self.assertEqual(False, calls[0][1])
        self.assertEqual("credentials.api_key", calls[0][2])
