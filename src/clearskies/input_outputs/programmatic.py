from __future__ import annotations

from typing import Any

from clearskies.input_outputs.headers import Headers
from clearskies.input_outputs.input_output import InputOutput


class Programmatic(InputOutput):
    _body: str | dict[str, Any] | list[Any] = ""
    url: str = ""
    ip_address: str = "127.0.0.1"
    protocol: str = "https"

    def __init__(
        self,
        url: str = "",
        request_method: str = "GET",
        body: str | dict[str, Any] | list[Any] = "",
        query_parameters: dict[str, Any] = {},
        request_headers: dict[str, str] = {},
        ip_address: str = "127.0.0.1",
        protocol: str = "https",
    ):
        self.url = url
        self.request_headers = Headers(request_headers)
        self.query_parameters = query_parameters
        self.ip_address = ip_address
        self.protocol = protocol
        self._body_loaded_as_json = True
        self._body_as_json = None
        self.request_method = request_method
        if body:
            self._body = body
            if isinstance(body, dict) or isinstance(body, list):
                self._body_as_json = body

        super().__init__()

    def respond(self, response, status_code=200):
        return (status_code, response, self.response_headers)

    def get_full_path(self):
        return self.url

    def has_body(self):
        return bool(self._body)

    def get_body(self):
        if not self.has_body():
            return ""

        return self._body

    def context_specifics(self):
        return {}

    def get_client_ip(self):
        return self.ip_address

    def get_protocol(self):
        return self.protocol
