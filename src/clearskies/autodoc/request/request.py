import re
from typing import Any


class Request:
    description: str = ""
    relative_path: str = ""
    request_methods: list[str] = []
    parameters: list[Any] = []
    responses = None
    root_properties = None

    def __init__(
        self, description, responses, relative_path="", request_methods="GET", parameters=None, root_properties=None
    ):
        # clearskies supports path parameters via {parameter} and :parameter but we want to normalize to {paramter} for
        # autodoc purposes
        if ":" in relative_path:
            relative_path = "/" + relative_path.strip("/") + "/"
            for match in re.findall("/(:[^/]+)/", relative_path):
                name = match[1:]
                relative_path = relative_path.replace(f"/:{name}/", "/{" + name + "}/")

        self.description = description
        self.responses = responses
        self.relative_path = relative_path.lstrip("/")
        self.request_methods = [request_methods] if type(request_methods) == str else request_methods
        self.set_parameters(parameters)
        self.root_properties = root_properties if root_properties is not None else {}

    def set_request_methods(self, request_methods):
        self.request_methods = [request_methods] if type(request_methods) == str else request_methods
        return self

    def prepend_relative_path(self, path):
        self.relative_path = path.rstrip("/") + "/" + self.relative_path.lstrip("/")
        return self

    def append_relative_path(self, path):
        self.relative_path = self.relative_path.rstrip("/") + "/" + path.lstrip("/")
        return self

    def set_parameters(self, parameters=None):
        self.parameters = parameters if parameters else []

    def add_parameter(self, parameter):
        self.parameters.append(parameter)
