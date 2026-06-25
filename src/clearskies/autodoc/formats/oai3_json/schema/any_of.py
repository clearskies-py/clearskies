class AnyOf:
    def __init__(self, schema, oai3_schema_resolver):
        self.schema = schema
        self.oai3_schema_resolver = oai3_schema_resolver

    def convert(self):
        return {
            "anyOf": [self.oai3_schema_resolver(option).convert() for option in self.schema.options],
        }
