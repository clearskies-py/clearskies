import re
from typing import Any

from ...schema import Object
from .parameter import Parameter
from .response import Response


class Request:
    formatted_responses: Any = None
    request: Any = None
    relative_path: str = ""

    def __init__(self, oai3_schema_resolver):
        self.oai3_schema_resolver = oai3_schema_resolver

    def set_request(self, request):
        self.request = request
        self.formatted_responses = [self.format_response(response) for response in self.request.responses]
        self.formatted_parameters = [
            self.format_parameter(parameter) for parameter in self.request.parameters if not parameter.in_body
        ]
        self.json_body_parameters = [parameter for parameter in self.request.parameters if parameter.in_body]
        self.relative_path = self.request.relative_path

    def format_response(self, response):
        formatted = Response(self.oai3_schema_resolver)
        formatted.set_response(response)
        return formatted

    def format_parameter(self, parameter):
        formatted = Parameter(self.oai3_schema_resolver)
        formatted.set_parameter(parameter)
        return formatted

    # Valid HTTP methods for OpenAPI 3.0
    VALID_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}

    def _generate_operation_id(self, method: str, path: str) -> str:
        """Generate a unique operationId from the HTTP method and path.

        Examples:
            GET /health -> getHealth
            GET /v3/api/users -> getV3ApiUsers
            GET /v3/api/users/{id} -> getV3ApiUsersById
            POST /v3/api/users -> postV3ApiUsers
        """
        # Remove leading/trailing slashes and replace {param} with ByParam
        clean_path = path.strip("/")
        # Replace {param} with ByParam (title case param name: first char upper, rest as-is)
        clean_path = re.sub(r"\{(\w+)\}", lambda m: "By" + m.group(1)[0].upper() + m.group(1)[1:], clean_path)
        # Split by / and title case each part (first char upper, rest as-is)
        parts = [part[0].upper() + part[1:] if part else "" for part in clean_path.split("/") if part]
        # Join and prepend with method
        return method.lower() + "".join(parts)

    def convert(self):
        data = {}
        for request_method in self.request.request_methods:
            method_lower = request_method.lower()
            # Skip invalid HTTP methods (e.g., "query" is not a valid OpenAPI method)
            if method_lower not in self.VALID_HTTP_METHODS:
                continue
            # Generate a default summary from the path and method if description is empty
            summary = self.request.description
            if not summary:
                # Create a human-readable summary from the path
                path_parts = self.relative_path.strip("/").replace("{", "").replace("}", "").split("/")
                summary = f"{method_lower.upper()} /{self.relative_path}"
            # Generate operationId from method and path
            operation_id = self._generate_operation_id(method_lower, self.relative_path)
            method_data: dict[str, Any] = {
                "operationId": operation_id,
                "summary": summary,
                "parameters": [parameter.convert() for parameter in self.formatted_parameters],
                "responses": {str(response.status_code): response.convert() for response in self.formatted_responses},
            }
            data[method_lower] = method_data

            if self.request.root_properties:
                data[method_lower] = {**data[method_lower], **self.request.root_properties}

            if self.json_body_parameters:
                # For OAI3, there should only be one JSON body root parameter, so it should either be an
                # object or an array.  If we have an array then wrap it in an object
                if type(self.json_body_parameters) == list:
                    definitions = [parameter.definition for parameter in self.json_body_parameters]
                    json_body = Object("body", definitions)
                    is_required = len([1 for param in self.json_body_parameters if param.required]) >= 1
                else:
                    json_body = self.json_body_parameters[0].definition
                    is_required = len([1 for param in json_body.definition.children if param.required]) >= 1

                data[method_lower]["requestBody"] = {
                    "description": self.request.description,
                    "required": is_required,
                    "content": {
                        "application/json": {
                            "schema": self.oai3_schema_resolver(json_body).convert(),
                        },
                    },
                }

        return data
