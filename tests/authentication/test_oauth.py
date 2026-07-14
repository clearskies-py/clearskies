import unittest
from unittest.mock import MagicMock, call

import clearskies


class TestOauth(unittest.TestCase):
    def test_basics(self):
        oauth = clearskies.authentication.Oauth(
            authentication_url="https://auth.example.com",
            secret_manager_secret_name="/path/to/client/credentials",
        )

        secrets = MagicMock()
        secrets.get = MagicMock(return_value={"client_id": "asdf", "client_secret": "qwerty"})

        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={"access_token": "ey=", "expires_in": 3600})
        requests = MagicMock()
        requests.post = MagicMock(return_value=response)

        di = clearskies.di.Di(
            bindings={
                "secrets": secrets,
                "requests": requests,
            }
        )
        di.inject_properties(oauth.__class__)

        headers = oauth.headers()
        assert headers == {"Authorization": "Bearer ey="}

        requests.post.assert_called_with(
            "https://auth.example.com",
            data={
                "grant_type": "client_credentials",
                "client_id": "asdf",
                "client_secret": "qwerty",
            },
        )

        secrets.get.assert_called_with("/path/to/client/credentials", silent_if_not_found=True)

    def test_secrets_return_json(self):
        oauth = clearskies.authentication.Oauth(
            authentication_url="https://auth.example.com",
            secret_manager_secret_name="/path/to/client/credentials",
        )

        secrets = MagicMock()
        secrets.get = MagicMock(return_value='{"client_id": "asdf", "client_secret": "qwerty"}')

        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={"access_token": "ey=", "expires_in": 3600})
        requests = MagicMock()
        requests.post = MagicMock(return_value=response)

        di = clearskies.di.Di(
            bindings={
                "secrets": secrets,
                "requests": requests,
            }
        )
        di.inject_properties(oauth.__class__)

        headers = oauth.headers()
        assert headers == {"Authorization": "Bearer ey="}

        requests.post.assert_called_with(
            "https://auth.example.com",
            data={
                "grant_type": "client_credentials",
                "client_id": "asdf",
                "client_secret": "qwerty",
            },
        )

        secrets.get.assert_called_with("/path/to/client/credentials", silent_if_not_found=True)

    def test_from_environment(self):
        oauth = clearskies.authentication.Oauth(
            authentication_url="https://auth.example.com",
            client_credentials_in_secret_manager=False,
        )

        environment = MagicMock()
        environment.get = MagicMock()
        environment.get.side_effect = ["zxcv", "pqwer"]

        response = MagicMock()
        response.status_code = 200
        response.json = MagicMock(return_value={"access_token": "ey=", "expires_in": 3600})
        requests = MagicMock()
        requests.post = MagicMock(return_value=response)

        di = clearskies.di.Di(
            bindings={
                "environment": environment,
                "requests": requests,
            }
        )
        di.inject_properties(oauth.__class__)

        headers = oauth.headers()
        assert headers == {"Authorization": "Bearer ey="}

        requests.post.assert_called_with(
            "https://auth.example.com",
            data={
                "grant_type": "client_credentials",
                "client_id": "zxcv",
                "client_secret": "pqwer",
            },
        )

        environment.get.assert_has_calls(
            [
                call("OAUTH_CLIENT_ID", silent=True),
                call("OAUTH_CLIENT_SECRET", silent=True),
            ]
        )
