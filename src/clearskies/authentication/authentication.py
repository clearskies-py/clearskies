from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests
import requests.auth
from requests.structures import CaseInsensitiveDict

import clearskies.configurable
from clearskies.authentication.authorization import Authorization

if TYPE_CHECKING:
    from clearskies.security_headers.cors import Cors


class Authentication(clearskies.configurable.Configurable, requests.auth.AuthBase):
    """Authentication."""

    is_public = True
    can_authorize = False
    has_dynamic_credentials = False
    max_auth_retries = 1

    def clear_credential_cache(self) -> None:
        pass

    def headers(self, retry_auth: bool = False) -> dict[str, str]:
        return {}

    def authenticate(self, input_output) -> bool:
        return True

    def authorize(self, authorization: Authorization):
        raise ValueError("Public endpoints do not support authorization")

    def set_headers_for_cors(self, cors: Cors):
        pass

    def documentation_security_scheme(self) -> dict[str, Any]:
        return {}

    def documentation_security_scheme_name(self) -> str:
        return ""

    def handle_401(self, response: requests.models.Response, *args: Any, **kwargs: Any) -> requests.models.Response:
        return self._retry_auth(response, **kwargs)

    def handle_403(self, response: requests.models.Response, *args: Any, **kwargs: Any) -> requests.models.Response:
        return self._retry_auth(response, **kwargs)

    def handle_default(self, response: requests.models.Response, *args: Any, **kwargs: Any) -> requests.models.Response:
        return response

    def handle_auth_response(
        self, response: requests.models.Response, *args: Any, **kwargs: Any
    ) -> requests.models.Response:
        handler = getattr(self, f"handle_{response.status_code}", self.handle_default)
        return handler(response, *args, **kwargs)

    def reauth(self, response: requests.models.Response, *args: Any, **kwargs: Any) -> requests.models.Response:
        return self.handle_auth_response(response, *args, **kwargs)

    def _retry_auth(self, response: requests.models.Response, **kwargs: Any) -> requests.models.Response:
        request = response.request
        if not request:
            return response

        retry_count = getattr(request, "_clearskies_auth_retry_count", 0)
        if retry_count >= self.max_auth_retries:
            return response

        retry_request = request.copy()
        retry_request.headers = CaseInsensitiveDict(dict(retry_request.headers or {}))
        retry_request.headers.update(self.headers(retry_auth=True))
        setattr(retry_request, "_clearskies_auth_retry_count", retry_count + 1)

        connection = getattr(response, "connection", None)
        if not connection:
            return response

        if getattr(response, "raw", None) and hasattr(response.raw, "drain_conn"):
            response.raw.drain_conn()
        else:
            _ = response.content
        response.close()
        return connection.send(retry_request, **kwargs)

    def __call__(self, r: requests.models.PreparedRequest) -> requests.models.PreparedRequest:
        r.register_hook("response", self.handle_auth_response)
        r.headers.update(self.headers())
        return r
