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

        schema = {
            "description": description,
            "content": {
                "application/json": {
                    "schema": self.oai3_schema_resolver(self.response.schema).convert(),
                }
            },
        }

        return schema
