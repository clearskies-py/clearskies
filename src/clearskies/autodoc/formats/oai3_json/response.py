from typing import Any


class Response:
    response: Any = None
    formatted_schema: Any = None
    oai3_schema_resolver: Any = None
    status_code: Any = None

    def __init__(self, oai3_schema_resolver):
        self.oai3_schema_resolver = oai3_schema_resolver

    def set_response(self, response):
        self.response = response
        self.status_code = self.response.status
        self.formatted_schema = self.oai3_schema_resolver(response.schema)

    def convert(self):
        # In OpenAPI 3.0, description is required for response objects
        description = self.response.description if self.response.description else "Response"

        content: dict[str, Any] = {}
        for content_type, content_data in self.response.content.items():
            response_schema = content_data.get("schema")
            converted_schema = self.oai3_schema_resolver(response_schema).convert() if response_schema else {}
            content[content_type] = {
                **content_data,
                "schema": converted_schema,
            }

        schema = {
            "description": description,
            "content": content,
        }

        if self.response.headers:
            schema["headers"] = self.response.headers

        if self.response.links:
            schema["links"] = {
                name: {
                    **({"operationId": link.operation_id} if getattr(link, "operation_id", "") else {}),
                    **({"operationRef": link.operation_ref} if getattr(link, "operation_ref", "") else {}),
                    **({"description": link.description} if getattr(link, "description", "") else {}),
                    **({"parameters": link.parameters} if getattr(link, "parameters", None) else {}),
                }
                for name, link in self.response.links.items()
            }

        return schema
