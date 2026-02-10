class Array:
    def __init__(self, schema, oai3_schema_resolver):
        self.schema = schema
        self.oai3_schema_resolver = oai3_schema_resolver

    def convert(self):
        schema = {
            "type": "array",
            "items": self.oai3_schema_resolver(self.schema.item_definition).convert(),
        }

        # Add nullable if the schema supports it
        if hasattr(self.schema, "nullable") and self.schema.nullable:
            schema["nullable"] = True

        return schema
