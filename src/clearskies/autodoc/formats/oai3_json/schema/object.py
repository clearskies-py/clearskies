from typing import Any


class Object:
    def __init__(self, schema, oai3_schema_resolver):
        self.schema = schema
        # shhhh - normalize children if they exist
        if self.schema.children:
            self.schema.children = [
                child[0] if (isinstance(child, tuple) or isinstance(child, list)) else child
                for child in self.schema.children
            ]

        self.oai3_schema_resolver = oai3_schema_resolver

    def convert(self, include_required=False):
        # If we have a model_name, use $ref only (no other properties allowed in OpenAPI 3.0)
        if self.schema.model_name:
            return {"$ref": f"#/components/schemas/{self.schema.model_name}"}

        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                schematic.name: self.oai3_schema_resolver(schematic).convert() for schematic in self.schema.children
            },
        }

        if include_required:
            required = self.required()
            if required:
                schema["required"] = required

        return schema

    def required(self):
        return [schematic.name for schematic in self.schema.children if schematic.required]
