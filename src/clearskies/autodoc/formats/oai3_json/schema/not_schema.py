class Not:
    def __init__(self, schema, oai3_schema_resolver):
        self.schema = schema
        self.oai3_schema_resolver = oai3_schema_resolver

    def convert(self):
        return {
            "not": self.oai3_schema_resolver(self.schema.option).convert(),
        }
