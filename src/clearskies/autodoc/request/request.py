from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from clearskies.autodoc.request.parameter import Parameter
    from clearskies.autodoc.response import Response


class Request:
    """
    Represent an API request for auto-documentation purposes.

    A Request captures the metadata needed to document a single API endpoint: its description,
    URL path, allowed HTTP methods, parameters, and expected responses.  It is the primary data
    structure consumed by the auto-documentation format renderers (e.g. OAI3 JSON).

    Path parameters using the `:name` syntax are automatically normalized to `{name}` for
    OpenAPI compatibility.
    """

    """A human-readable description of what this request does."""
    description: str = ""

    """The relative URL path for this request, with path parameters in `{name}` format."""
    relative_path: str = ""

    """The HTTP methods allowed for this request (e.g. ["GET"], ["POST", "PUT"])."""
    request_methods: list[str] = []

    """The list of parameters (URL, query, JSON body, headers) accepted by this request."""
    parameters: list[Parameter] = []

    """The expected responses for this request, keyed by status code."""
    responses: list[Response] | None = None

    """Additional top-level properties to include in the documentation output."""
    root_properties: dict[str, Any] | None = None

    def __init__(
        self,
        description: str,
        responses: list[Response],
        relative_path: str = "",
        request_methods: str | list[str] = "GET",
        parameters: list[Parameter] | None = None,
        root_properties: dict[str, Any] | None = None,
    ):
        # clearskies supports path parameters via {parameter} and :parameter but we want to normalize to {parameter} for
        # autodoc purposes
        if ":" in relative_path:
            relative_path = "/" + relative_path.strip("/") + "/"
            for match in re.findall("/(:[^/]+)/", relative_path):
                name = match[1:]
                relative_path = relative_path.replace(f"/:{name}/", "/{" + name + "}/")
            # Remove trailing slash added for regex matching
            relative_path = relative_path.rstrip("/")

        self.description = description
        self.responses = responses
        self.relative_path = relative_path.lstrip("/")
        self.request_methods = [request_methods] if isinstance(request_methods, str) else list(request_methods)
        self.set_parameters(parameters)
        self.root_properties = root_properties if root_properties is not None else {}

    def set_request_methods(self, request_methods: str | list[str]) -> Self:
        """Set the allowed HTTP methods for this request."""
        self.request_methods = [request_methods] if isinstance(request_methods, str) else request_methods
        return self

    def prepend_relative_path(self, path: str) -> Self:
        """Prepend a path segment to the beginning of the relative path."""
        self.relative_path = path.rstrip("/") + "/" + self.relative_path.lstrip("/")
        return self

    def append_relative_path(self, path: str) -> Self:
        """Append a path segment to the end of the relative path."""
        self.relative_path = self.relative_path.rstrip("/") + "/" + path.lstrip("/")
        return self

    def set_parameters(self, parameters: list[Parameter] | None = None) -> None:
        """Set the list of parameters for this request."""
        self.parameters = list(parameters) if parameters else []

    def add_parameter(self, parameter: Parameter) -> None:
        """Add a single parameter to this request."""
        self.parameters.append(parameter)
