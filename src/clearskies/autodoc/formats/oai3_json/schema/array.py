class Array:
    def __init__(self, schema, oai3_schema_resolver):
        self.schema = schema
        self.oai3_schema_resolver = oai3_schema_resolver

    def convert(self):
        schema = {
            "type": "array",
            "items": self.oai3_schema_resolver(self.schema.item_definition).convert(),
        }

        if hasattr(self.schema, "min_items") and self.schema.min_items is not None:
            schema["minItems"] = self.schema.min_items
        if hasattr(self.schema, "max_items") and self.schema.max_items is not None:
            schema["maxItems"] = self.schema.max_items
        if hasattr(self.schema, "unique_items") and self.schema.unique_items is not None:
            schema["uniqueItems"] = self.schema.unique_items

        # Add nullable if the schema supports it
        if hasattr(self.schema, "nullable") and self.schema.nullable:
            schema["nullable"] = True

        return schema
