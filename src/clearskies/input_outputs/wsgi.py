from __future__ import annotations

import json
from typing import Callable
from urllib.parse import parse_qs

from clearskies.input_outputs.headers import Headers
from clearskies.input_outputs.input_output import InputOutput


class Wsgi(InputOutput):
    _environment: dict[str, str] = {}
    _start_response: Callable
    _cached_body: str | None = None

    def __init__(self, environment, start_response):
        self._environment = environment
        self._start_response = start_response
        request_headers = {}
        for key, value in self._environment.items():
            if key.upper()[0:5] == "HTTP_":
                request_headers[key[5:].lower()] = value

        self.request_headers = Headers(request_headers)
        self.query_parameters = {
            key: val[0] for (key, val) in parse_qs(self._environment.get("QUERY_STRING", "")).items()
        }
        self.request_method = self._environment.get("REQUEST_METHOD").upper()

        super().__init__()

    def _from_environment(self, key):
        return self._environment[key] if key in self._environment else ""

    def respond(self, body, status_code=200):
        if "content-type" not in self.response_headers:
            self.response_headers.content_type = "application/json; charset=UTF-8"

        self._start_response(f"{status_code} Ok", [header for header in self.response_headers.items()])  # type: ignore
        if type(body) == bytes:
            final_body = body
        elif type(body) == str:
            final_body = body.encode("utf-8")
        else:
            final_body = json.dumps(body).encode("utf-8")
        return [final_body]

    def has_body(self):
        return bool(self._from_environment("CONTENT_LENGTH"))

    def get_body(self):
        if self._cached_body is None:
            self._cached_body = (
                self._from_environment("wsgi.input").read(int(self._from_environment("CONTENT_LENGTH"))).decode("utf-8")
                if self._from_environment("CONTENT_LENGTH")
                else ""
            )
        return self._cached_body

    def get_script_name(self):
        return self._from_environment("SCRIPT_NAME")

    def get_path_info(self):
        return self._from_environment("PATH_INFO")

    def get_full_path(self):
        path_info = self.get_path_info()
        script_name = self.get_script_name()
        if not path_info or path_info[0] != "/":
            path_info = f"/{path_info}"
        return f"{path_info}{script_name}".replace("//", "/")

    def get_protocol(self):
        return self._from_environment("wsgi.url_scheme").lower()

    def context_specifics(self):
        return {"wsgi_environment": self._environment}

    def get_client_ip(self):
        return self._environment.get("REMOTE_ADDR")
