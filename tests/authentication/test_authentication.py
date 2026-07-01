import unittest
from typing import Any, cast

import requests

from clearskies.authentication.authentication import Authentication


class TrackingAuthentication(Authentication):
    def __init__(self):
        self.header_calls = []

    def headers(self, retry_auth: bool = False) -> dict[str, str]:
        self.header_calls.append(retry_auth)
        if retry_auth:
            return {"Authorization": "Bearer refreshed-token"}
        return {"Authorization": "Bearer initial-token"}


class FakeConnection:
    def __init__(self):
        self.sent_request = None
        self.sent_kwargs = {}

    def send(self, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        self.sent_request = request
        self.sent_kwargs = kwargs
        response = requests.Response()
        response.status_code = 200
        response._content = b""
        return response


class AuthenticationTest(unittest.TestCase):
    def test_call_sets_initial_headers_and_reauth_hook(self):
        auth = TrackingAuthentication()
        request = requests.Request("GET", "https://example.com").prepare()

        result = auth(request)

        self.assertIs(result, request)
        self.assertEqual("Bearer initial-token", request.headers["Authorization"])
        self.assertEqual([False], auth.header_calls)
        self.assertIn(auth.reauth, request.hooks["response"])

    def test_reauth_retries_401_with_refreshed_headers(self):
        auth = TrackingAuthentication()
        request = requests.Request("GET", "https://example.com").prepare()
        request = auth(request)

        response = requests.Response()
        response.status_code = 401
        response.request = request
        response._content = b""
        connection = FakeConnection()
        setattr(response, "connection", cast(Any, connection))

        retry_response = auth.reauth(response, timeout=2)

        self.assertEqual(200, retry_response.status_code)
        self.assertEqual([False, True], auth.header_calls)
        self.assertIsNotNone(connection.sent_request)
        sent_request = cast(requests.PreparedRequest, connection.sent_request)
        self.assertEqual("Bearer refreshed-token", sent_request.headers["Authorization"])
        self.assertEqual(1, getattr(connection.sent_request, "_clearskies_auth_retry_count", 0))
        self.assertEqual({"timeout": 2}, connection.sent_kwargs)

    def test_reauth_retries_403_with_refreshed_headers(self):
        auth = TrackingAuthentication()
        request = requests.Request("GET", "https://example.com").prepare()
        request = auth(request)

        response = requests.Response()
        response.status_code = 403
        response.request = request
        response._content = b""
        connection = FakeConnection()
        setattr(response, "connection", cast(Any, connection))

        retry_response = auth.reauth(response)

        self.assertEqual(200, retry_response.status_code)
        self.assertEqual([False, True], auth.header_calls)

    def test_reauth_returns_original_response_when_connection_missing(self):
        auth = TrackingAuthentication()
        request = requests.Request("GET", "https://example.com").prepare()
        request = auth(request)

        response = requests.Response()
        response.status_code = 401
        response.request = request

        same_response = auth.reauth(response)

        self.assertIs(same_response, response)

    def test_reauth_respects_max_retries(self):
        auth = TrackingAuthentication()
        request = requests.Request("GET", "https://example.com").prepare()
        setattr(request, "_clearskies_auth_retry_count", auth.max_auth_retries)

        response = requests.Response()
        response.status_code = 401
        response.request = request

        same_response = auth.reauth(response)

        self.assertIs(same_response, response)
